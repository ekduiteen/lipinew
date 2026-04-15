from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from services import speaker_clustering as speaker_clustering_svc
from services import speaker_embeddings as speaker_embeddings_svc


class _MockResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


@pytest.mark.asyncio
async def test_extract_embedding_rejects_wrong_dimensions():
    http = AsyncMock()
    http.post = AsyncMock(
        return_value=_MockResponse(
            {
                "embedding": [0.1] * 128,
                "dimensions": 128,
                "duration_ms": 1800,
                "quality": "good",
                "latency_ms": 10,
                "model": "broken",
            }
        )
    )

    with pytest.raises(speaker_embeddings_svc.SpeakerEmbeddingError):
        await speaker_embeddings_svc.extract_embedding(http=http, audio_bytes=b"fake-audio")


@pytest.mark.asyncio
async def test_extract_and_store_skips_low_quality_turn():
    db = AsyncMock()
    http = AsyncMock()

    stored, reason = await speaker_embeddings_svc.extract_and_store(
        db=db,
        http=http,
        teacher_id="t1",
        session_id="s1",
        audio_path="raw-teacher-audio/t1/s1/sample.bin",
        detected_language="ne",
        stt_confidence=0.4,
        hearing_result={"learning_allowed": True, "audio_duration_ms": 2200},
    )

    assert stored is False
    assert reason.startswith("low_stt_confidence")
    db.execute.assert_not_awaited()
    http.post.assert_not_awaited()


@pytest.mark.asyncio
async def test_extract_and_store_persists_vector(monkeypatch):
    async def _fake_fetch(_: str | None) -> bytes | None:
        return b"fake-audio"

    monkeypatch.setattr(
        speaker_embeddings_svc.audio_storage_svc,
        "fetch_teacher_audio",
        _fake_fetch,
    )
    monkeypatch.setattr(
        speaker_embeddings_svc.speaker_clustering_svc,
        "assign_cluster",
        AsyncMock(return_value=7),
    )

    http = AsyncMock()
    http.post = AsyncMock(
        return_value=_MockResponse(
            {
                "embedding": [0.01] * 512,
                "dimensions": 512,
                "duration_ms": 2200,
                "quality": "good",
                "latency_ms": 12,
                "model": "acoustic_signature_v1",
            }
        )
    )
    db = AsyncMock()

    stored, reason = await speaker_embeddings_svc.extract_and_store(
        db=db,
        http=http,
        teacher_id="t1",
        session_id="s1",
        audio_path="raw-teacher-audio/t1/s1/sample.bin",
        detected_language="new",
        stt_confidence=0.91,
        hearing_result={"learning_allowed": True, "audio_duration_ms": 2200},
    )

    assert stored is True
    assert reason == "stored"
    db.execute.assert_awaited()


def test_choose_cluster_for_embedding_prefers_nearest_match():
    target = [1.0, 0.0, 0.0]
    candidates = [
        (2, [0.0, 1.0, 0.0]),
        (4, [0.99, 0.01, 0.0]),
    ]

    cluster_id = speaker_clustering_svc.choose_cluster_for_embedding(
        target,
        candidates,
        threshold=0.8,
    )

    assert cluster_id == 4
