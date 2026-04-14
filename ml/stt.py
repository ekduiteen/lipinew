"""STT service — faster-whisper large-v3 with built-in VAD."""

import io
import logging
import time

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

logger = logging.getLogger("lipi.ml.stt")


class STTService:
    """Wraps faster-whisper for Nepali/English transcription."""

    def __init__(
        self,
        device: str = "cuda:0",
        model_size: str = "large-v3",
        compute_type: str = "float16",
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

    def transcribe(self, audio_bytes: bytes) -> dict:
        """Transcribe audio bytes. Auto-detects language (ne/en)."""
        start = time.perf_counter()

        audio_array, sample_rate = sf.read(io.BytesIO(audio_bytes), dtype="float32")
        if audio_array.ndim > 1:
            audio_array = audio_array.mean(axis=1)
        if sample_rate != 16000:
            # faster-whisper resamples internally if given raw float32
            pass

        segments, info = self.model.transcribe(
            audio_array,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            language=None,  # auto-detect
        )

        segments_list = list(segments)
        text = " ".join(seg.text.strip() for seg in segments_list).strip()

        avg_logprob = (
            float(np.mean([seg.avg_logprob for seg in segments_list]))
            if segments_list else 0.0
        )
        confidence = float(np.exp(avg_logprob)) if segments_list else 0.0

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        return {
            "text": text,
            "language": info.language,
            "confidence": confidence,
            "duration_ms": elapsed_ms,
        }
