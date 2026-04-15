"""
Tests for services/stt.py and services/tts.py

Covers:
- STT: local primary path, Groq fallback, error with no fallback key
- TTS: successful synthesis, failure returns empty bytes, empty text returns empty bytes
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx


# ─── STT ────────────────────────────────────────────────────────────────────

class TestSTTTranscribe:
    @pytest.mark.asyncio
    async def test_local_stt_primary_path(self):
        """transcribe() returns local STT result on success."""
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "text": "नमस्ते",
            "language": "ne",
            "confidence": 0.97,
            "duration_ms": 850,
        }
        mock_http.post = AsyncMock(return_value=mock_resp)

        from services.stt import transcribe
        result = await transcribe(b"fake-audio", mock_http)

        assert result["text"] == "नमस्ते"
        assert result["confidence"] == 0.97
        mock_http.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_groq_fallback_on_local_stt_failure(self):
        """When local STT fails, Groq Whisper is activated."""
        mock_http = AsyncMock(spec=httpx.AsyncClient)

        local_error_resp = MagicMock()
        local_error_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "503", request=MagicMock(), response=MagicMock()
        )
        groq_resp = MagicMock()
        groq_resp.raise_for_status = MagicMock()
        groq_resp.json.return_value = {
            "text": "नमस्ते",
            "language": "ne",
        }
        mock_http.post = AsyncMock(side_effect=[local_error_resp, groq_resp])

        with patch("services.stt.settings") as mock_settings:
            mock_settings.ml_service_url = "http://ml:5001"
            mock_settings.ml_timeout = 10.0
            mock_settings.groq_api_key = "test-groq-key"

            from services.stt import transcribe
            result = await transcribe(b"fake-audio", mock_http)

        assert result["text"] == "नमस्ते"
        assert result["confidence"] == 0.9  # Groq fixed confidence
        assert mock_http.post.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_when_local_fails_and_no_groq_key(self):
        """With no Groq key, local STT failure propagates."""
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.post = AsyncMock(side_effect=httpx.ConnectError("refused"))

        with patch("services.stt.settings") as mock_settings:
            mock_settings.ml_service_url = "http://ml:5001"
            mock_settings.ml_timeout = 10.0
            mock_settings.groq_api_key = ""

            from services.stt import transcribe
            with pytest.raises(httpx.ConnectError):
                await transcribe(b"fake-audio", mock_http)

    @pytest.mark.asyncio
    async def test_groq_result_normalises_shape(self):
        """Groq response is normalised to match local STT schema."""
        mock_http = AsyncMock(spec=httpx.AsyncClient)

        local_error_resp = MagicMock()
        local_error_resp.raise_for_status.side_effect = httpx.ConnectError("down")
        groq_resp = MagicMock()
        groq_resp.raise_for_status = MagicMock()
        groq_resp.json.return_value = {"text": "hello", "language": "en"}
        mock_http.post = AsyncMock(side_effect=[local_error_resp, groq_resp])

        with patch("services.stt.settings") as mock_settings:
            mock_settings.ml_service_url = "http://ml:5001"
            mock_settings.ml_timeout = 10.0
            mock_settings.groq_api_key = "key"

            from services.stt import transcribe
            result = await transcribe(b"audio", mock_http)

        # Must always return all 4 keys
        assert {"text", "language", "confidence", "duration_ms"} <= result.keys()


# ─── TTS ────────────────────────────────────────────────────────────────────

class TestTTSSynthesize:
    @pytest.mark.asyncio
    async def test_returns_wav_bytes_on_success(self):
        """synthesize() returns raw bytes from ML service."""
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.content = b"RIFF....fake-wav-data"
        mock_http.post = AsyncMock(return_value=mock_resp)

        from services.tts import synthesize
        result = await synthesize("नमस्ते", mock_http)

        assert result == b"RIFF....fake-wav-data"
        mock_http.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_empty_bytes_on_failure(self):
        """TTS failure returns b'' (no Groq fallback for TTS)."""
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.post = AsyncMock(side_effect=httpx.ConnectError("tts down"))

        from services.tts import synthesize
        result = await synthesize("नमस्ते", mock_http)

        assert result == b""

    @pytest.mark.asyncio
    async def test_empty_text_returns_empty_bytes_without_calling_service(self):
        """synthesize() short-circuits on empty/whitespace text."""
        mock_http = AsyncMock(spec=httpx.AsyncClient)

        from services.tts import synthesize
        result = await synthesize("   ", mock_http)

        assert result == b""
        mock_http.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_http_status_error_returns_empty_bytes(self):
        """A 500 from the ML service returns b'' rather than propagating."""
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=MagicMock()
        )
        mock_http.post = AsyncMock(return_value=mock_resp)

        from services.tts import synthesize
        result = await synthesize("नमस्ते", mock_http)

        assert result == b""


# ─── _silent_wav ────────────────────────────────────────────────────────────

class TestSilentWav:
    def test_returns_valid_wav_header(self):
        from services.tts import _silent_wav
        wav = _silent_wav(100)
        # WAV files start with "RIFF"
        assert wav[:4] == b"RIFF"

    def test_returns_bytes(self):
        from services.tts import _silent_wav
        assert isinstance(_silent_wav(200), bytes)
