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
    """Wraps faster-whisper for Nepali/English transcription."""

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
    ) -> dict:
        """Transcribe audio bytes. Auto-detects language (ne/en)."""
        start = time.perf_counter()

        audio_array, sample_rate = sf.read(io.BytesIO(audio_bytes), dtype="float32")
        if audio_array.ndim > 1:
            audio_array = audio_array.mean(axis=1)

        if len(audio_array) < _MIN_AUDIO_SAMPLES:
            return self._empty_result(start)

        rms = float(np.sqrt(np.mean(np.square(audio_array)))) if len(audio_array) else 0.0
        if rms < _MIN_RMS:
            return self._empty_result(start)

        if sample_rate != 16000:
            # faster-whisper resamples internally if given raw float32
            pass

        attempts: list[str | None] = []
        seen: set[str | None] = set()
        preferred_hint = (language_hint or self.language_hint or "").strip() or None
        active_prompt = (prompt or self.initial_prompt or "").strip() or None

        for candidate in (preferred_hint, "en", None):
            if candidate not in seen:
                seen.add(candidate)
                attempts.append(candidate)

        best_result: dict | None = None

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
                    return self._empty_result(start)
                raise

            segments_list = list(segments)
            candidate_text = " ".join(seg.text.strip() for seg in segments_list).strip()
            avg_logprob = (
                float(np.mean([seg.avg_logprob for seg in segments_list]))
                if segments_list else 0.0
            )
            candidate_confidence = float(np.exp(avg_logprob)) if segments_list else 0.0
            candidate_result = {
                "text": candidate_text,
                "language": info.language,
                "confidence": candidate_confidence,
            }

            if candidate_text and (
                best_result is None
                or candidate_confidence > best_result["confidence"] + 0.03
                or (
                    candidate_confidence >= best_result["confidence"] - 0.02
                    and language == preferred_hint
                )
            ):
                best_result = candidate_result

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        if best_result is None:
            return self._empty_result(start)

        return {
            "text": best_result["text"],
            "language": best_result["language"],
            "confidence": best_result["confidence"],
            "duration_ms": elapsed_ms,
        }

    def _empty_result(self, start: float) -> dict:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return {
            "text": "",
            "language": "ne",
            "confidence": 0.0,
            "duration_ms": elapsed_ms,
        }
