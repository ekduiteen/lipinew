"""Tests for Safe Hybrid Pivot Architecture"""

import pytest
import httpx
from unittest.mock import AsyncMock

from services.audio_understanding import extract_audio_signals, AudioUnderstandingResult
from services.input_understanding import merge_signals
from services.hearing import HearingResult
from services.turn_interpreter import TurnInterpretation


@pytest.mark.asyncio
async def test_audio_understanding_fallback_on_missing_audio():
    """Test that audio_understanding degrades gracefully when no audio is provided."""
    mock_http = AsyncMock(spec=httpx.AsyncClient)
    
    result = await extract_audio_signals(
        http=mock_http,
        audio_uri=None,
        audio_bytes=None,
        rough_transcript="namaste"
    )
    
    assert isinstance(result, AudioUnderstandingResult)
    assert result.model_source == "fallback"
    assert result.dialect_guess is None
    # Ensure it didn't block or crash
    mock_http.post.assert_not_called()


@pytest.mark.asyncio
async def test_audio_understanding_fallback_on_api_timeout():
    """Test that audio_understanding degrades gracefully on external ML API timeout."""
    mock_http = AsyncMock(spec=httpx.AsyncClient)
    mock_http.post.side_effect = httpx.TimeoutException("mock timeout")
    
    result = await extract_audio_signals(
        http=mock_http,
        audio_bytes=b"dummy",
        rough_transcript="kasto chha"
    )
    
    assert isinstance(result, AudioUnderstandingResult)
    assert result.model_source == "fallback"
    assert mock_http.post.call_count == 1


def test_input_understanding_merges_signals_safely():
    """Test that input_understanding merges Whisper (Hearing) and Gemma (AudioUnderstanding)."""
    hearing = HearingResult(
        raw_text="timi kasto chau",
        clean_text="timi kasto chau",
        language="ne",
        confidence=0.88,
        mode="speech",
        quality_label="good",
        audio_quality_score=0.88,
        audio_duration_ms=1800,
        learning_allowed=True,
        conversation_allowed=True,
        reason_codes=[],
    )
    
    interpreter = TurnInterpretation(
        intent_type="unknown",
        active_topic="everyday_basics",
        is_correction=False,
        taught_terms=[],
        register_hint="timi",
        emotion_hint=None,
        user_goal="continue_conversation",
        candidate_followup_zones=[],
    )
    
    # Simulate a successful audio understanding extraction
    audio_signals = AudioUnderstandingResult(
        primary_language="ne",
        secondary_languages=["en"],
        code_switch_ratio=0.5,
        tone="friendly",
        emotion="neutral",
        is_correction=False,
        is_teaching=False,
        topic="everyday_basics",
        dialect_guess="kathmandu",
        dialect_confidence=0.9,
        speech_rate="fast",
        prosody_pattern="rising",
        pronunciation_style="standard",
        register_estimate="timi",
        model_source="gemma_audio_v1",
        model_confidence=0.85
    )
    
    result = merge_signals(
        turn_id="test_turn",
        hearing=hearing,
        interpretation=interpreter,
        audio_signals=audio_signals
    )
    
    # Assert merged properly
    assert result.primary_language == "ne"
    assert result.dialect_guess == "kathmandu"
    assert result.tone == "friendly"
    assert result.signal_confidences["stt"] == 0.88
    assert result.code_switch_ratio == 0.5
    assert result.transcript_confidence == 0.88
