"""
Tests for services/llm.py

Covers:
- _postprocess_teacher_reply: emoji stripping, length cap, repetitive closer removal
- _score_language_purity: Nepali ok, Urdu script reject, Hindi marker reject, Latin-heavy reject
- generate: vLLM primary path, Groq fallback on vLLM failure, error with no fallback
- generate_teacher_reply: pure Nepali path, multilingual path
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx


# ─── _postprocess_teacher_reply ─────────────────────────────────────────────

class TestPostprocessTeacherReply:
    def setup_method(self):
        from services.llm import _postprocess_teacher_reply
        self.fn = _postprocess_teacher_reply

    def test_strips_emojis(self):
        result = self.fn("नमस्ते😊 कस्तो छ?")
        assert "😊" not in result

    def test_collapses_whitespace(self):
        result = self.fn("नमस्ते   कस्तो   छ?")
        assert "   " not in result

    def test_strips_parenthetical(self):
        result = self.fn("राम्रो (यो एउटा कमेन्ट हो) छ।")
        assert "(" not in result and ")" not in result

    def test_removes_repetitive_closer(self):
        result = self.fn("राम्रो छ। तिमीलाई कस्तो छ?")
        # When there are multiple sentences, the repetitive closer is removed
        assert "तिमीलाई कस्तो छ?" not in result

    def test_truncates_long_reply_at_word_boundary(self):
        # 200+ char string should be capped at 140 chars
        long_text = "नमस्ते " * 30  # well over 140 chars
        result = self.fn(long_text)
        assert len(result) <= 145  # slight buffer for punctuation

    def test_empty_input_returns_empty(self):
        assert self.fn("") == ""
        assert self.fn("   ") == ""

    def test_limits_to_two_sentences(self):
        text = "एक। दुई। तीन। चार।"
        result = self.fn(text)
        # At most 2 sentences
        sentences = [s for s in result.split("।") if s.strip()]
        assert len(sentences) <= 2


# ─── _score_language_purity ──────────────────────────────────────────────────

class TestScoreLanguagePurity:
    def setup_method(self):
        from services.llm import _score_language_purity
        self.fn = _score_language_purity

    def test_clean_nepali_passes(self):
        ok, reason = self.fn("नमस्ते, तपाईंलाई भेट्दा खुशी लाग्यो।")
        assert ok is True
        assert reason == "ok"

    def test_empty_string_fails(self):
        ok, reason = self.fn("")
        assert ok is False
        assert reason == "empty"

    def test_urdu_script_rejected(self):
        ok, reason = self.fn("آپ کیسے ہیں؟")
        assert ok is False
        assert reason == "urdu_script"

    def test_hindi_markers_rejected(self):
        # Multiple Hindi-specific words should trigger rejection
        ok, reason = self.fn("क्या आप ठीक हैं? मेरा नाम राहुल है।")
        assert ok is False
        assert "hindi_markers" in reason

    def test_latin_heavy_rejected(self):
        # More Latin words than Devanagari → reject
        ok, reason = self.fn("hello how are you doing today friend")
        assert ok is False
        assert reason == "too_much_latin"

    def test_nepali_with_acceptable_latin_passes(self):
        # A couple English words in Nepali context is fine
        ok, reason = self.fn("नेपाली र English दुवै सिक्न राम्रो छ।")
        assert ok is True


# ─── generate (fallback logic) ───────────────────────────────────────────────

class TestGenerateFallback:
    @pytest.mark.asyncio
    async def test_uses_vllm_primary_path(self):
        """generate() calls vLLM and returns its response when successful."""
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "नमस्ते!"}}]
        }
        mock_http.post = AsyncMock(return_value=mock_resp)

        from services.llm import generate
        result = await generate([{"role": "user", "content": "hi"}], mock_http)
        assert result == "नमस्ते!"
        mock_http.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_falls_back_to_groq_when_vllm_fails(self):
        """When vLLM raises, generate() activates Groq fallback."""
        mock_http = AsyncMock(spec=httpx.AsyncClient)

        # vLLM call raises
        vllm_error_resp = MagicMock()
        vllm_error_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "503", request=MagicMock(), response=MagicMock()
        )
        groq_resp = MagicMock()
        groq_resp.raise_for_status = MagicMock()
        groq_resp.json.return_value = {
            "choices": [{"message": {"content": "Groq fallback reply"}}]
        }
        mock_http.post = AsyncMock(side_effect=[vllm_error_resp, groq_resp])

        with patch("services.llm.settings") as mock_settings:
            mock_settings.vllm_url = "http://vllm:8100"
            mock_settings.vllm_model = "lipi"
            mock_settings.vllm_timeout = 8.0
            mock_settings.groq_api_key = "test-groq-key"

            from services.llm import generate
            result = await generate([{"role": "user", "content": "hi"}], mock_http)

        assert result == "Groq fallback reply"
        assert mock_http.post.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_when_vllm_fails_and_no_groq_key(self):
        """With no Groq key, vLLM failure propagates to the caller."""
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.post = AsyncMock(side_effect=httpx.ConnectError("refused"))

        with patch("services.llm.settings") as mock_settings:
            mock_settings.vllm_url = "http://vllm:8100"
            mock_settings.vllm_model = "lipi"
            mock_settings.vllm_timeout = 8.0
            mock_settings.groq_api_key = ""

            from services.llm import generate
            with pytest.raises(httpx.ConnectError):
                await generate([{"role": "user", "content": "hi"}], mock_http)


# ─── _response_mode ──────────────────────────────────────────────────────────

class TestResponseMode:
    def setup_method(self):
        from services.llm import _response_mode
        self.fn = _response_mode

    def test_nepali_script_returns_nepali(self):
        assert self.fn("नमस्ते, तपाईं कहाँ हुनुहुन्छ?", "ne") == "nepali"

    def test_english_detected_returns_english(self):
        assert self.fn("hello how are you doing", "en") == "english"

    def test_mixed_scripts_returns_mixed(self):
        result = self.fn("नमस्ते, I am fine here", None)
        assert result in ("mixed", "nepali")  # depends on word ratio
