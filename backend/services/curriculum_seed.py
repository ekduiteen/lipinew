"""Seed helpers for curriculum taxonomy and baseline coverage rows."""

from __future__ import annotations

from services.curriculum import QUESTION_TYPES, TOPIC_TAXONOMY


SEED_LANGUAGES = ("ne", "en", "new")
SEED_REGISTERS = ("hajur", "tapai", "timi", "ta")


def seeded_topic_rows() -> list[dict]:
    return [
        {
            "topic_key": topic.topic_key,
            "display_name": topic.display_name,
            "description": topic.description,
            "example_question_intents": list(topic.example_question_intents),
            "allowed_question_types": list(topic.allowed_question_types),
            "difficulty_level": topic.difficulty_level,
            "diversity_priority": topic.diversity_priority,
        }
        for topic in TOPIC_TAXONOMY.values()
    ]


def seeded_question_type_rows() -> list[dict]:
    return [
        {"question_type": key, "description": description}
        for key, description in QUESTION_TYPES.items()
    ]
