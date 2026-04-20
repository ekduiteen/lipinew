from services.hearing import HearingResult
from services import response_cleanup as response_cleanup_svc


def _hearing(mode: str = "ne") -> HearingResult:
    return HearingResult(
        raw_text="",
        clean_text="",
        confidence=0.9,
        language=mode,
        mode=mode,
        quality_label="good",
        audio_quality_score=0.9,
        audio_duration_ms=None,
        conversation_allowed=True,
        learning_allowed=True,
        reason_codes=[],
    )


def test_finalize_reply_strips_turn_markers_and_leaked_role_prefixes():
    cleaned = response_cleanup_svc.finalize_reply(
        "<end_of_turn> <start_of_turn>user यसलाई सवापिक रुपमैत मेरो टौको।",
        _hearing(),
    )

    assert "<" not in cleaned
    assert not cleaned.lower().startswith("user ")
    assert "यसलाई सवापिक रुपमैत मेरो टौको" in cleaned


def test_finalize_reply_falls_back_when_only_turn_markers_remain():
    cleaned = response_cleanup_svc.finalize_reply(
        "<end_of_turn> <start_of_turn>assistant",
        _hearing(),
    )

    assert cleaned == "म अलि बुझिनँ। फेरि भन्न सक्छौ?"
