"""TTS service - Piper Nepali voice with cached local model files."""

from __future__ import annotations

import io
import logging
import os
import wave
from pathlib import Path
from urllib.request import urlretrieve

import numpy as np

logger = logging.getLogger("lipi.ml.tts")

_DEFAULT_SAMPLE_RATE = 22050
_DEFAULT_VOICE = "ne_NP-google-medium"
_VOICE_FILES = {
    "ne_NP-google-medium": {
        "model": "https://huggingface.co/rhasspy/piper-voices/resolve/main/ne/ne_NP/google/medium/ne_NP-google-medium.onnx",
        "config": "https://huggingface.co/rhasspy/piper-voices/resolve/main/ne/ne_NP/google/medium/ne_NP-google-medium.onnx.json",
    },
    "ne_NP-chitwan-medium": {
        "model": "https://huggingface.co/rhasspy/piper-voices/resolve/main/ne/ne_NP/chitwan/medium/ne_NP-chitwan-medium.onnx",
        "config": "https://huggingface.co/rhasspy/piper-voices/resolve/main/ne/ne_NP/chitwan/medium/ne_NP-chitwan-medium.onnx.json",
    },
}


def _download_if_missing(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return
    logger.info("Downloading Piper asset %s", target.name)
    urlretrieve(url, target)


class TTSService:
    """Wrap Piper for fast local Nepali speech synthesis."""

    def __init__(
        self,
        device: str = "cpu",
        voice_id: str | None = None,
        speaker_id: int | None = None,
        length_scale: float | None = None,
        sentence_silence: float | None = None,
    ):
        del device
        from piper import PiperVoice

        self.voice_id = voice_id or os.getenv("PIPER_VOICE_ID", _DEFAULT_VOICE)
        self.speaker_id = int(os.getenv("PIPER_SPEAKER_ID", str(speaker_id if speaker_id is not None else 0)))
        self.length_scale = float(os.getenv("PIPER_LENGTH_SCALE", str(length_scale if length_scale is not None else 1.25)))
        self.sentence_silence = float(
            os.getenv("PIPER_SENTENCE_SILENCE", str(sentence_silence if sentence_silence is not None else 0.15))
        )
        self.model_dir = Path(os.getenv("PIPER_MODEL_DIR", "/app/models/piper"))

        voice_files = _VOICE_FILES.get(self.voice_id)
        if not voice_files:
            raise RuntimeError(f"Unsupported Piper voice id: {self.voice_id}")

        model_path = self.model_dir / self.voice_id / f"{self.voice_id}.onnx"
        config_path = self.model_dir / self.voice_id / f"{self.voice_id}.onnx.json"
        _download_if_missing(voice_files["model"], model_path)
        _download_if_missing(voice_files["config"], config_path)

        logger.info(
            "Loading Piper voice %s",
            self.voice_id,
        )
        self.voice = PiperVoice.load(str(model_path), str(config_path))
        self.sample_rate = getattr(self.voice.config, "sample_rate", _DEFAULT_SAMPLE_RATE)

    def synthesize(self, text: str, language: str = "ne") -> tuple[np.ndarray, int]:
        del language
        if not text.strip():
            return np.zeros(0, dtype=np.float32), self.sample_rate

        wave_io = io.BytesIO()
        with wave.open(wave_io, "wb") as wav_file:
            self.voice.synthesize_wav(text, wav_file)

        wave_io.seek(0)
        with wave.open(wave_io, "rb") as wav_file:
            frames = wav_file.readframes(wav_file.getnframes())
            sample_rate = wav_file.getframerate()

        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        return audio, sample_rate
