"""Auto-generate phrases from LLM when supply runs low."""

from __future__ import annotations

import asyncio
import logging
import json
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from config import settings
from models.phrases import Phrase, PhraseGenerationBatch
from db.connection import SessionLocal

logger = logging.getLogger("lipi.backend.phrase_generator")

CATEGORIES = ["greetings", "questions", "politeness", "introductions", "statements", "requests", "daily_life", "emotions", "food", "travel"]

MIN_ACTIVE_PHRASES = 20  # Regenerate when below this threshold


async def generate_phrase_batch(
    http: httpx.AsyncClient,
    category: str,
    count: int = 5
) -> list[dict]:
    """Generate phrases from LLM (Gemma 4)."""
    prompt = f"""Generate {count} Nepali phrases with English translations for the category: {category}.

Format as JSON array:
[{{"text_ne": "नेपाली", "text_en": "English", "category": "{category}"}}]

Only return valid JSON, no extra text."""

    try:
        response = await http.post(
            f"{settings.vllm_url}/v1/chat/completions",
            json={
                "model": settings.vllm_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 1000,
            },
            timeout=15.0
        )
        response.raise_for_status()
        data = response.json()

        # Extract text from response
        content = data["choices"][0]["message"]["content"].strip()

        # Parse JSON
        phrases = json.loads(content)
        if isinstance(phrases, dict):
            phrases = [phrases]

        return phrases[:count]  # Limit to requested count

    except Exception as exc:
        logger.error(f"Phrase generation failed: {exc}")
        return []


async def auto_generate_phrases(http: httpx.AsyncClient) -> None:
    """Background job: Generate phrases when supply runs low."""
    while True:
        try:
            async with SessionLocal() as db:
                # Check active phrase count
                result = await db.execute(
                    select(func.count(Phrase.id)).where(Phrase.is_active == True)
                )
                active_count = result.scalar() or 0

                if active_count < MIN_ACTIVE_PHRASES:
                    logger.info(f"Phrase supply low ({active_count}). Generating more...")

                    # Generate phrases for each category
                    for category in CATEGORIES:
                        phrases = await generate_phrase_batch(http, category, count=3)

                        for phrase_data in phrases:
                            phrase = Phrase(
                                text_en=phrase_data.get("text_en", ""),
                                text_ne=phrase_data.get("text_ne", ""),
                                category=phrase_data.get("category", category),
                                is_active=True,
                                review_status="approved",  # Trust LLM for MVP
                                created_by="phrase_generator"
                            )
                            db.add(phrase)

                    await db.commit()
                    logger.info(f"Generated {len(CATEGORIES) * 3} phrases")

        except Exception as exc:
            logger.error(f"Auto-generate job error: {exc}")

        # Check every 5 minutes
        await asyncio.sleep(300)
