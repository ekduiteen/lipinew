"""STT service — faster-whisper large-v3 with built-in VAD."""

import io
import logging
import os
import time

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

logger = logging.getLogger("lipi.ml.stt")

_MIN_AUDIO_SAMPLES = 1600
_MIN_RMS = 0.003


class STTService:
    """Wraps faster-whisper for country-anchored multi-candidate transcription."""

    def __init__(
        self,
        device: str = "cuda:0",
        model_size: str = "large-v3",
        compute_type: str = "float16",
        language_hint: str | None = None,
        initial_prompt: str | None = None,
    ):
        device_type, _, device_index = device.partition(":")
        self.device = device_type
        self.device_index = int(device_index) if device_index else 0

        logger.info(
            "Loading faster-whisper %s on %s:%d (%s)",
            model_size, self.device, self.device_index, compute_type,
        )
        self.model = WhisperModel(
            model_size,
            device=self.device,
            device_index=self.device_index,
            compute_type=compute_type,
        )
        self.language_hint = (language_hint or os.getenv("WHISPER_LANGUAGE_HINT", "ne")).strip() or None
        self.initial_prompt = (
            initial_prompt
            or os.getenv(
                "WHISPER_INITIAL_PROMPT",
                "नमस्ते। म नेपाली बोल्छु। तपाईं, तिमी, म, नेपाली, भाषा, शिक्षक, लिपि।",
            )
        ).strip()

    def transcribe(
        self,
        audio_bytes: bytes,
        *,
        prompt: str | None = None,
        language_hint: str | None = None,
        candidate_languages: list[str] | None = None,
        base_asr_languages: list[str] | None = None,
        target_language: str | None = None,
        enable_auto_candidate: bool = True,
    ) -> dict:
        """Transcribe audio bytes and return multi-candidate ASR output."""
        start = time.perf_counter()

        audio_array, sample_rate = sf.read(io.BytesIO(audio_bytes), dtype="float32")
        if audio_array.ndim > 1:
            audio_array = audio_array.mean(axis=1)

        if len(audio_array) < _MIN_AUDIO_SAMPLES:
            return self._empty_result(start, target_language=target_language, base_asr_languages=base_asr_languages)

        rms = float(np.sqrt(np.mean(np.square(audio_array)))) if len(audio_array) else 0.0
        if rms < _MIN_RMS:
            return self._empty_result(start, target_language=target_language, base_asr_languages=base_asr_languages)

        if sample_rate != 16000:
            # faster-whisper resamples internally if given raw float32
            pass

        attempts: list[str | None] = []
        seen: set[str | None] = set()
        preferred_hint = (language_hint or self.language_hint or "").strip() or None
        active_prompt = (prompt or self.initial_prompt or "").strip() or None

        for candidate in candidate_languages or []:
            code = (candidate or "").strip() or None
            if code not in seen:
                seen.add(code)
                attempts.append(code)
        if preferred_hint not in seen:
            seen.add(preferred_hint)
            attempts.append(preferred_hint)
        if enable_auto_candidate and None not in seen:
            seen.add(None)
            attempts.append(None)

        candidate_results: list[dict] = []

        for language in attempts:
            try:
                segments, info = self.model.transcribe(
                    audio_array,
                    beam_size=5,
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 500},
                    language=language,
                    initial_prompt=active_prompt if language == preferred_hint else None,
                )
            except ValueError as exc:
                if "empty sequence" in str(exc):
                    logger.info("STT received silence/empty audio after VAD; returning empty transcript")
                    return self._empty_result(start, target_language=target_language, base_asr_languages=base_asr_languages)
                raise

            segments_list = list(segments)
            candidate_text = " ".join(seg.text.strip() for seg in segments_list).strip()
            avg_logprob = (
                float(np.mean([seg.avg_logprob for seg in segments_list]))
                if segments_list else 0.0
            )
            candidate_confidence = float(np.exp(avg_logprob)) if segments_list else 0.0
            candidate_result = {
                "candidate_type": self._candidate_type(
                    requested_language=language,
                    reported_language=info.language,
                    base_asr_languages=base_asr_languages or [],
                    target_language=target_language,
                ),
                "language_code": (language or info.language or "unknown"),
                "detected_language": info.language,
                "transcript": candidate_text,
                "confidence": candidate_confidence,
                "model_name": "faster-whisper-large-v3",
                "adapter_name": target_language if language and target_language and language == target_language else None,
            }
            candidate_results.append(candidate_result)

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        non_empty_candidates = [candidate for candidate in candidate_results if candidate["transcript"]]
        if not non_empty_candidates:
            return self._empty_result(start, target_language=target_language, base_asr_languages=base_asr_languages)

        best_result = self._select_candidate(
            candidates=non_empty_candidates,
            base_asr_languages=base_asr_languages or [],
            target_language=target_language,
        )
        return {
            "text": best_result["transcript"],
            "language": best_result.get("detected_language") or best_result["language_code"],
            "selected_transcript": best_result["transcript"],
            "selected_language": best_result["language_code"],
            "detected_language": best_result.get("detected_language") or best_result["language_code"],
            "target_language": target_language,
            "base_asr_languages": base_asr_languages or [],
            "confidence": best_result["confidence"],
            "duration_ms": elapsed_ms,
            "candidates": self._rank_candidates(candidate_results, best_result),
        }

    def _empty_result(
        self,
        start: float,
        *,
        target_language: str | None,
        base_asr_languages: list[str] | None,
    ) -> dict:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return {
            "text": "",
            "language": "ne",
            "selected_transcript": "",
            "selected_language": "",
            "detected_language": "ne",
            "target_language": target_language,
            "base_asr_languages": base_asr_languages or [],
            "confidence": 0.0,
            "duration_ms": elapsed_ms,
            "candidates": [],
        }

    def _candidate_type(
        self,
        *,
        requested_language: str | None,
        reported_language: str | None,
        base_asr_languages: list[str],
        target_language: str | None,
    ) -> str:
        requested = (requested_language or "").lower()
        reported = (reported_language or "").lower()
        target = (target_language or "").lower()
        base = {str(item).lower() for item in base_asr_languages}

        if not requested_language:
            return "whisper_auto"
        if requested == target and target and target not in base:
            return "target_adapter"
        if requested == "ne":
            return "base_nepali"
        if requested == "en":
            return "base_english"
        if requested == target:
            return "target_adapter"
        if reported == "en":
            return "base_english"
        if reported == "ne":
            return "base_nepali"
        return "candidate"

    def _select_candidate(
        self,
        *,
        candidates: list[dict],
        base_asr_languages: list[str],
        target_language: str | None,
    ) -> dict:
        target = (target_language or "").lower()
        base = {str(item).lower() for item in base_asr_languages}

        def sort_key(candidate: dict) -> tuple[float, float, float]:
            language_code = str(candidate.get("language_code") or "").lower()
            candidate_type = str(candidate.get("candidate_type") or "")
            confidence = float(candidate.get("confidence") or 0.0)
            adapter_bonus = 0.2 if candidate_type == "target_adapter" and language_code == target else 0.0
            target_bonus = 0.1 if language_code == target and target else 0.0
            base_bonus = 0.05 if language_code in base else 0.0
            return (confidence + adapter_bonus + target_bonus + base_bonus, target_bonus, confidence)

        return max(candidates, key=sort_key)

    def _rank_candidates(self, candidates: list[dict], best_result: dict) -> list[dict]:
        ranked = sorted(candidates, key=lambda item: float(item.get("confidence") or 0.0), reverse=True)
        output: list[dict] = []
        for index, candidate in enumerate(ranked, start=1):
            candidate_copy = dict(candidate)
            candidate_copy["rank"] = index
            candidate_copy["selected"] = candidate is best_result or (
                candidate.get("transcript") == best_result.get("transcript")
                and candidate.get("language_code") == best_result.get("language_code")
            )
            output.append(candidate_copy)
        return output
