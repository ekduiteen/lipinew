from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import BytesIO
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from models.admin_control import AdminAccount, AdminAuditLog
from models.dataset_gold import DatasetSnapshot, GoldRecord
from models.intelligence import ReviewQueueItem
from services import admin_moderation as admin_moderation_svc


def _admin(admin_id: str, email: str, role: str = "moderator") -> AdminAccount:
    return AdminAccount(
        id=admin_id,
        email=email,
        full_name=email.split("@")[0],
        role=role,
        is_active=True,
    )


def _review_item(
    *,
    item_id: str,
    extracted_claim: str,
    confidence: float,
    metadata: dict,
    model_source: str = "hybrid_input_understanding",
) -> ReviewQueueItem:
    return ReviewQueueItem(
        id=item_id,
        source_audio_path="audio.wav",
        source_transcript=extracted_claim,
        teacher_id=None,
        session_id=None,
        extracted_claim=extracted_claim,
        extraction_metadata=metadata,
        confidence=confidence,
        model_source=model_source,
        status="pending_review",
    )


@pytest.mark.asyncio
async def test_queue_claiming_is_exclusive_and_releases_expired_claims(db_session):
    admin_one = _admin("a0000000-0000-0000-0000-000000000101", "mod1@example.com")
    admin_two = _admin("a0000000-0000-0000-0000-000000000102", "mod2@example.com")
    first_item = _review_item(
        item_id=str(uuid.uuid4()),
        extracted_claim="भात",
        confidence=0.9,
        metadata={"correction_event_id": "c1", "language_key": "ne"},
    )
    second_item = _review_item(
        item_id=str(uuid.uuid4()),
        extracted_claim="पानी",
        confidence=0.6,
        metadata={"review_kind": "low_trust_extraction", "language_key": "ne"},
        model_source="learning_validation_guard",
    )
    db_session.add_all([admin_one, admin_two, first_item, second_item])
    await db_session.commit()

    filters = admin_moderation_svc.ModerationFilters()
    claimed_one = await admin_moderation_svc.claim_next_review_item(
        db_session,
        admin=admin_one,
        filters=filters,
    )
    claimed_two = await admin_moderation_svc.claim_next_review_item(
        db_session,
        admin=admin_two,
        filters=filters,
    )

    assert claimed_one is not None
    assert claimed_two is not None
    assert claimed_one.id != claimed_two.id

    first_item.claimed_by = admin_one.id
    first_item.claimed_at = datetime.now(timezone.utc) - admin_moderation_svc.CLAIM_TIMEOUT - timedelta(minutes=1)
    second_item.status = "approved"
    await db_session.commit()

    reclaimed = await admin_moderation_svc.claim_next_review_item(
        db_session,
        admin=admin_two,
        filters=filters,
    )

    assert reclaimed is not None
    assert reclaimed.id == first_item.id


@pytest.mark.asyncio
async def test_queue_filters_return_expected_subset(db_session):
    admin = _admin("a0000000-0000-0000-0000-000000000103", "mod3@example.com")
    correction_item = _review_item(
        item_id=str(uuid.uuid4()),
        extracted_claim="भात",
        confidence=0.92,
        metadata={"correction_event_id": "c2", "language_key": "ne"},
    )
    low_trust_item = _review_item(
        item_id=str(uuid.uuid4()),
        extracted_claim="rice",
        confidence=0.21,
        metadata={"review_kind": "low_trust_extraction", "language_key": "en"},
        model_source="learning_validation_guard",
    )
    db_session.add_all([admin, correction_item, low_trust_item])
    await db_session.commit()

    items, total = await admin_moderation_svc.list_review_queue(
        db_session,
        admin=admin,
        filters=admin_moderation_svc.ModerationFilters(
            review_type="low_trust_extraction",
            language="en",
            source="model",
            confidence_max=0.5,
        ),
    )

    assert total == 1
    assert len(items) == 1
    assert items[0].id == low_trust_item.id


@pytest.mark.asyncio
async def test_batch_approve_is_atomic_and_creates_gold(db_session):
    admin = _admin("a0000000-0000-0000-0000-000000000104", "mod4@example.com")
    item_one = _review_item(
        item_id=str(uuid.uuid4()),
        extracted_claim="भात",
        confidence=0.9,
        metadata={"language_key": "ne"},
    )
    item_two = _review_item(
        item_id=str(uuid.uuid4()),
        extracted_claim="पानी",
        confidence=0.8,
        metadata={"language_key": "ne"},
    )
    db_session.add_all([admin, item_one, item_two])
    await db_session.commit()

    gold_records = await admin_moderation_svc.batch_label_and_promote_to_gold(
        db_session,
        item_specs=[
            {"id": item_one.id, "register": "Tapai"},
            {"id": item_two.id, "register": "Tapai"},
        ],
        admin=admin,
    )

    await db_session.refresh(item_one)
    await db_session.refresh(item_two)
    gold_count = len((await db_session.execute(select(GoldRecord))).scalars().all())

    assert len(gold_records) == 2
    assert item_one.status == "approved"
    assert item_two.status == "approved"
    assert gold_count == 2


@pytest.mark.asyncio
async def test_real_metrics_endpoint_and_snapshot_download(client, db_session, monkeypatch):
    from dependencies.admin_auth import get_current_admin
    from main import app

    admin = _admin("a0000000-0000-0000-0000-000000000105", "mod5@example.com")
    queue_item = _review_item(
        item_id=str(uuid.uuid4()),
        extracted_claim="rice",
        confidence=0.3,
        metadata={"review_kind": "low_trust_extraction", "language_key": "en"},
        model_source="learning_validation_guard",
    )
    queue_item.claimed_by = admin.id
    queue_item.claimed_at = datetime.now(timezone.utc)

    snapshot = DatasetSnapshot(
        id=str(uuid.uuid4()),
        dataset_name="ne-standard",
        version="1.0.0",
        record_count=2,
        filter_query={"language": "ne"},
        download_url="datasets/example.zip",
        created_by=admin.id,
    )
    db_session.add_all(
        [
            admin,
            queue_item,
            snapshot,
            GoldRecord(
                id=str(uuid.uuid4()),
                original_message_id=None,
                session_id=None,
                teacher_id=None,
                audio_path=None,
                raw_transcript="raw",
                corrected_transcript="clean",
                primary_language="ne",
                dialect="Kathmandu",
                register="Tapai",
                tags=[],
                audio_quality_score=0.95,
                noise_level="low",
                labeled_by=admin.id,
            ),
            AdminAuditLog(
                admin_id=admin.id,
                action="approve_and_label",
                entity_type="GoldRecord",
                entity_id="gold-1",
                details={},
            ),
        ]
    )
    await db_session.commit()

    class _FakeStream:
        def __init__(self, payload: bytes):
            self._payload = payload
            self._sent = False

        def read(self, _size: int) -> bytes:
            if self._sent:
                return b""
            self._sent = True
            return self._payload

        def close(self):
            return None

        def release_conn(self):
            return None

    async def _override_admin():
        return admin

    app.dependency_overrides[get_current_admin] = _override_admin
    monkeypatch.setattr("routes.admin_export.open_snapshot_stream", lambda _: _FakeStream(b"zip-bytes"))

    try:
        metrics_response = await client.get("/api/ctrl/system/metrics/real")
        assert metrics_response.status_code == 200
        metrics = metrics_response.json()
        assert metrics["pending_queue_size"] >= 1
        assert metrics["items_claimed"] >= 1
        assert metrics["gold_records_created"] >= 1

        download_response = await client.get(f"/api/ctrl/datasets/download/{snapshot.id}")
        assert download_response.status_code == 200
        assert download_response.content == b"zip-bytes"
        assert download_response.headers["content-type"] == "application/zip"
    finally:
        app.dependency_overrides.clear()
