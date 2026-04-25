from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models.training_export import TrainingExport


EXPORT_ROOT = Path("/data/exports")


async def export_training_rows(
    db: AsyncSession,
    *,
    country_code: str,
    target_language: str | None = None,
    tier: str = "gold",
) -> dict:
    export_dir = EXPORT_ROOT / country_code / (target_language or "all")
    export_dir.mkdir(parents=True, exist_ok=True)

    params = {"country_code": country_code, "tier": tier}
    language_filter = ""
    if target_language:
        params["target_language"] = target_language
        language_filter = "AND m.target_language = :target_language"

    rows = await db.execute(
        text(
            f"""
            SELECT m.id AS message_id, m.audio_path, m.country_code, m.target_language,
                   COALESCE(s.base_asr_languages, '[]') AS base_asr_languages,
                   m.script, m.dialect_label,
                   raw_stt, base_candidate_transcript, english_candidate_transcript, target_candidate_transcript,
                   teacher_corrected_transcript, normalized_transcript, training_tier, asr_drift_type,
                   correction_error_type, audio_quality, stt_confidence, m.teacher_id, m.consent_training_use, m.created_at
            FROM messages m
            LEFT JOIN teaching_sessions s ON s.id = m.session_id
            WHERE m.role = 'teacher'
              AND m.country_code = :country_code
              {language_filter}
              AND m.training_tier = :tier
              AND m.training_eligible = true
            ORDER BY m.created_at ASC
            """
        ),
        params,
    )
    items = [dict(row) for row in rows.mappings().all()]

    output_path = export_dir / f"asr_{tier}.jsonl"
    with output_path.open("w", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")

    metadata_path = export_dir / "metadata.jsonl"
    with metadata_path.open("w", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "country_code": country_code,
                    "target_language": target_language,
                    "tier": tier,
                    "sample_count": len(items),
                    "export_path": str(output_path),
                },
                ensure_ascii=False,
            )
            + "\n"
        )

    db.add(
        TrainingExport(
            country_code=country_code,
            target_language=target_language,
            export_type=f"asr_{tier}",
            export_path=str(output_path),
            sample_count=len(items),
            total_audio_seconds=sum(
                float(item.get("audio_duration_ms") or 0.0) / 1000.0 for item in items
            ),
            metadata_json={"metadata_path": str(metadata_path)},
        )
    )
    await db.flush()

    return {
        "country_code": country_code,
        "target_language": target_language,
        "tier": tier,
        "sample_count": len(items),
        "export_path": str(output_path),
        "metadata_path": str(metadata_path),
    }
