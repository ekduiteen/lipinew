"""Tests for the learning queue quality gate and JSON extraction."""

import json
import pytest


class TestLearningQualityGate:
    """Tests for _should_learn_from_turn module-level function."""

    def _make_stt_result(self, confidence: float = 0.95, language: str = "ne") -> dict:
        return {"confidence": confidence, "language": language, "text": "test"}

    def test_high_confidence_nepali_is_eligible(self):
        from services.learning import _should_learn_from_turn

        eligible, reason = _should_learn_from_turn(
            teacher_text="नमस्ते, तपाईं कस्तो हुनुहुन्छ?",
            lipi_response="म राम्रोसँग छु, धन्यवाद।",
            stt_result=self._make_stt_result(confidence=0.95, language="ne"),
        )
        assert eligible is True
        assert reason == "ok"

    def test_low_confidence_stt_is_not_eligible(self):
        from services.learning import _should_learn_from_turn

        eligible, reason = _should_learn_from_turn(
            teacher_text="something unclear",
            lipi_response="ok fine",
            stt_result=self._make_stt_result(confidence=0.3, language="ne"),
        )
        assert eligible is False
        assert "low_stt_confidence" in reason

    def test_english_speech_is_not_eligible(self):
        from services.learning import _should_learn_from_turn

        eligible, reason = _should_learn_from_turn(
            teacher_text="Hello, how are you?",
            lipi_response="Fine thank you",
            stt_result=self._make_stt_result(confidence=0.95, language="en"),
        )
        assert eligible is False
        assert "teacher_language" in reason

    def test_too_short_teacher_text_is_not_eligible(self):
        from services.learning import _should_learn_from_turn

        eligible, reason = _should_learn_from_turn(
            teacher_text="हा",  # Only 2 chars
            lipi_response="राम्रो",
            stt_result=self._make_stt_result(confidence=0.95),
        )
        assert eligible is False
        assert "too_short" in reason

    def test_confused_reply_is_not_eligible(self):
        from services.learning import _should_learn_from_turn, _CONFUSED_REPLY_MARKERS

        if not _CONFUSED_REPLY_MARKERS:
            pytest.skip("No confusion markers defined")

        confused_marker = next(iter(_CONFUSED_REPLY_MARKERS))
        eligible, reason = _should_learn_from_turn(
            teacher_text="नमस्ते के गर्दैछ?",
            lipi_response=f"राम्रो {confused_marker} भएन",
            stt_result=self._make_stt_result(confidence=0.95),
        )
        assert eligible is False
        assert reason == "assistant_confused"


class TestExtractionJSONParsing:
    """Test the JSON parsing logic used in _process_job (inline in learning.py)."""

    def _parse_extraction(self, raw: str) -> list[dict]:
        """Replicate the JSON parsing logic from learning.py._process_job."""
        try:
            cleaned = (
                raw.strip()
                .removeprefix("```json")
                .removeprefix("```")
                .removesuffix("```")
                .strip()
            )
            payload = json.loads(cleaned)
            words = payload.get("words", [])
            if not isinstance(words, list):
                return []
            return words
        except (json.JSONDecodeError, AttributeError):
            return []

    def test_valid_json_extraction(self):
        raw = json.dumps({
            "words": [
                {"word": "घर", "language": "ne", "definition_en": "house"},
                {"word": "पानी", "language": "ne", "definition_en": "water"},
            ]
        })
        words = self._parse_extraction(raw)
        assert len(words) == 2
        assert words[0]["word"] == "घर"

    def test_malformed_json_returns_empty(self):
        result = self._parse_extraction("not json at all {broken")
        assert result == []

    def test_non_list_words_returns_empty(self):
        raw = json.dumps({"words": "घर पानी"})  # String instead of list
        result = self._parse_extraction(raw)
        assert result == []

    def test_markdown_fenced_json_is_stripped(self):
        raw = '```json\n{"words": [{"word": "घर", "language": "ne", "definition_en": "house"}]}\n```'
        words = self._parse_extraction(raw)
        assert len(words) == 1
        assert words[0]["word"] == "घर"

    def test_empty_words_list(self):
        raw = json.dumps({"words": []})
        result = self._parse_extraction(raw)
        assert result == []
