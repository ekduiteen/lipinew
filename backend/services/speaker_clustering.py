"""Lightweight incremental clustering for speaker embeddings."""

from __future__ import annotations

import json
import math
from collections import Counter

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_SIMILARITY_THRESHOLD = 0.94
_CANDIDATE_LIMIT = 200


def _parse_vector_text(value: str) -> list[float]:
    stripped = (value or "").strip()
    if not stripped:
        return []
    return [float(item) for item in json.loads(stripped)]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)


def choose_cluster_for_embedding(
    target_embedding: list[float],
    candidates: list[tuple[int, list[float]]],
    *,
    threshold: float = _SIMILARITY_THRESHOLD,
) -> int | None:
    best_cluster_id: int | None = None
    best_score = -1.0
    for cluster_id, candidate_embedding in candidates:
        score = _cosine_similarity(target_embedding, candidate_embedding)
        if score > best_score:
            best_score = score
            best_cluster_id = cluster_id
    if best_cluster_id is None or best_score < threshold:
        return None
    return best_cluster_id


async def assign_cluster(
    db: AsyncSession,
    *,
    embedding_id: str,
    detected_language: str | None,
) -> int | None:
    row = (
        await db.execute(
            text(
                """
                SELECT embedding::text AS embedding_text, detected_language
                FROM speaker_embeddings
                WHERE id = :id
                """
            ),
            {"id": embedding_id},
        )
    ).mappings().first()
    if row is None:
        return None

    language_key = str(detected_language or row["detected_language"] or "unknown")
    target_embedding = _parse_vector_text(str(row["embedding_text"] or "[]"))
    if not target_embedding:
        return None

    candidates_rows = (
        await db.execute(
            text(
                """
                SELECT dialect_cluster_id, embedding::text AS embedding_text
                FROM speaker_embeddings
                WHERE id <> :id
                  AND detected_language = :language_key
                  AND dialect_cluster_id IS NOT NULL
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"id": embedding_id, "language_key": language_key, "limit": _CANDIDATE_LIMIT},
        )
    ).mappings().all()
    candidates = [
        (int(row["dialect_cluster_id"]), _parse_vector_text(str(row["embedding_text"] or "[]")))
        for row in candidates_rows
        if row["dialect_cluster_id"] is not None
    ]

    chosen_cluster = choose_cluster_for_embedding(target_embedding, candidates)
    if chosen_cluster is None:
        max_cluster = (
            await db.execute(text("SELECT COALESCE(MAX(dialect_cluster_id), 0) FROM speaker_embeddings"))
        ).scalar_one()
        chosen_cluster = int(max_cluster or 0) + 1

    await db.execute(
        text(
            """
            UPDATE speaker_embeddings
            SET dialect_cluster_id = :cluster_id
            WHERE id = :id
            """
        ),
        {"cluster_id": chosen_cluster, "id": embedding_id},
    )
    return chosen_cluster


async def get_cluster_summary(db: AsyncSession) -> dict:
    total_embeddings = int(
        (
            await db.execute(text("SELECT COUNT(*) FROM speaker_embeddings"))
        ).scalar_one()
        or 0
    )
    assigned_embeddings = int(
        (
            await db.execute(
                text("SELECT COUNT(*) FROM speaker_embeddings WHERE dialect_cluster_id IS NOT NULL")
            )
        ).scalar_one()
        or 0
    )
    cluster_count = int(
        (
            await db.execute(
                text("SELECT COUNT(DISTINCT dialect_cluster_id) FROM speaker_embeddings WHERE dialect_cluster_id IS NOT NULL")
            )
        ).scalar_one()
        or 0
    )
    by_language_rows = (
        await db.execute(
            text(
                """
                SELECT COALESCE(detected_language, 'unknown') AS language_key, COUNT(*) AS count
                FROM speaker_embeddings
                GROUP BY COALESCE(detected_language, 'unknown')
                ORDER BY count DESC
                """
            )
        )
    ).mappings().all()
    cluster_rows = (
        await db.execute(
            text(
                """
                SELECT dialect_cluster_id, COUNT(*) AS count
                FROM speaker_embeddings
                WHERE dialect_cluster_id IS NOT NULL
                GROUP BY dialect_cluster_id
                ORDER BY count DESC, dialect_cluster_id ASC
                LIMIT 12
                """
            )
        )
    ).mappings().all()
    languages = {
        str(row["language_key"]): int(row["count"] or 0)
        for row in by_language_rows
    }
    top_clusters = [
        {"cluster_id": int(row["dialect_cluster_id"]), "count": int(row["count"] or 0)}
        for row in cluster_rows
    ]
    return {
        "total_embeddings": total_embeddings,
        "assigned_embeddings": assigned_embeddings,
        "cluster_count": cluster_count,
        "embeddings_by_language": languages,
        "top_clusters": top_clusters,
    }
