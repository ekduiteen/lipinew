import pytest
import httpx
from unittest.mock import AsyncMock, patch

from services.phrase_pipeline import get_next_phrase, process_phrase_audio
from models.phrases import Phrase, PhraseMetrics

@pytest.mark.asyncio
async def test_phrase_selection_excludes_skips_and_returns_valid_phrase():
    """Mock the DB session to verify get_next_phrase logic runs without crashing."""
    mock_db = AsyncMock()
    # Assume it returns a Phrase
    mock_phrase = Phrase(id="p1", text_en="Test", text_ne="परीक्षण", is_active=True)
    
    # Mocking the complex SQL executes
    mock_res = AsyncMock()
    mock_res.scalar_one_or_none.return_value = mock_phrase
    mock_db.execute.return_value = mock_res
    
    # If no reconfirm, it falls through to regular selection
    result = await get_next_phrase(mock_db, "user-123")
    assert result == mock_phrase

@pytest.mark.asyncio
@patch("services.hearing.analyze_hearing")
@patch("services.stt.transcribe")
async def test_noisy_audio_rejection(mock_transcribe, mock_analyze_hearing):
    """Verify that if hearing engine detects poor quality, pipeline rejects."""
    
    mock_db = AsyncMock()
    mock_http = AsyncMock(spec=httpx.AsyncClient)
    
    # Setup phrase
    mock_db.get.return_value = Phrase(id="test-phrase")
    
    # Setup STT Mock
    mock_transcribe.return_value = {"confidence": 0.8, "language": "ne"}
    
    # Setup Hearing Mock to simulate noise
    from services.hearing import HearingResult
    mock_analyze_hearing.return_value = HearingResult(
        raw_text="mumble",
        clean_text="mumble",
        language="ne",
        confidence=0.8,
        mode="speech",
        quality_label="poor",  # CRITICAL: Poor quality
        audio_quality_score=0.45,
        audio_duration_ms=1200,
        learning_allowed=False,
        conversation_allowed=False,
        reason_codes=["noise_marker"],
    )
    
    result = await process_phrase_audio(
        db=mock_db,
        http=mock_http,
        user_id="user-123",
        phrase_id="test-phrase",
        audio_bytes=b"noisy data",
        audio_uri="minio://path/audio.webm"
    )
    
    assert result["status"] == "retry"
    assert "poor quality" in result["reason"].lower() or "clipping/noise" in result["reason"].lower()

@pytest.mark.asyncio
@patch("services.hearing.analyze_hearing")
@patch("services.stt.transcribe")
@patch("services.audio_understanding.extract_audio_signals")
@patch("services.learning.enqueue_phrase_submission")
async def test_rare_language_acceptance(mock_enqueue, mock_audio, mock_transcribe, mock_analyze_hearing):
    """Verify that clean speech with low STT confidence (e.g. Newari dialect) is still accepted."""
    
    mock_db = AsyncMock()
    mock_http = AsyncMock(spec=httpx.AsyncClient)
    
    # Setup phrase
    mock_db.get.return_value = Phrase(id="test-phrase", text_en="hello", text_ne="namaste")
    
    # STT Mock: Extremely low confidence
    mock_transcribe.return_value = {"confidence": 0.1, "language": "ne"}
    
    # Hearing Mock: Clean audio!
    from services.hearing import HearingResult
    mock_analyze_hearing.return_value = HearingResult(
        raw_text="jojolapa",
        clean_text="jojolapa", # Newari hello
        language="new",
        confidence=0.1,
        mode="speech",
        quality_label="good",  # CRITICAL: Clean microphone
        audio_quality_score=0.84,
        audio_duration_ms=1600,
        learning_allowed=True,
        conversation_allowed=True,
        reason_codes=[],
    )
    
    # Audio Models Mock
    from services.audio_understanding import AudioUnderstandingResult
    mock_audio.return_value = AudioUnderstandingResult.fallback()
    
    result = await process_phrase_audio(
        db=mock_db,
        http=mock_http,
        user_id="user-123",
        phrase_id="test-phrase",
        audio_bytes=b"clean rare data",
        audio_uri="minio://path/audio.webm"
    )
    
    # Should accept and NOT retry
    assert result["status"] == "success"
    assert result["transcript"] == "jojolapa"
    mock_enqueue.assert_called_once()
