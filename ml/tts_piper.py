"""Piper TTS provider — reliable Nepali/English fallback."""

from __future__ import annotations

import io
import logging
import os
import wave
from pathlib import Path
from urllib.request import urlretrieve

import numpy as np

from tts_provider import TTSProvider

logger = logging.getLogger("lipi.ml.tts_piper")

_DEFAULT_SAMPLE_RATE = 22050
_DEFAULT_VOICE = "ne_NP-google-medium"
_DEFAULT_ENGLISH_VOICE = "en_US-lessac-medium"
_VOICE_FILES = {
    "ne_NP-google-medium": {
        "model": "https://huggingface.co/rhasspy/piper-voices/resolve/main/ne/ne_NP/google/medium/ne_NP-google-medium.onnx",
        "config": "https://huggingface.co/rhasspy/piper-voices/resolve/main/ne/ne_NP/google/medium/ne_NP-google-medium.onnx.json",
    },
    "ne_NP-chitwan-medium": {
        "model": "https://huggingface.co/rhasspy/piper-voices/resolve/main/ne/ne_NP/chitwan/medium/ne_NP-chitwan-medium.onnx",
        "config": "https://huggingface.co/rhasspy/piper-voices/resolve/main/ne/ne_NP/chitwan/medium/ne_NP-chitwan-medium.onnx.json",
    },
    "en_US-lessac-medium": {
        "model": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
        "config": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json",
    },
}


def _download_if_missing(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return
    logger.info("Downloading Piper asset %s", target.name)
    urlretrieve(url, target)


class PiperProvider(TTSProvider):
    """Piper TTS — good Nepali voice, reliable fallback for all languages."""

    def __init__(
        self,
        voice_id: str | None = None,
        speaker_id: int | None = None,
        length_scale: float | None = None,
        sentence_silence: float | None = None,
    ):
        from piper import PiperVoice  # noqa: F401  (import-check at init)

        self.nepali_voice_id = os.getenv(
            "PIPER_VOICE_ID_NE",
            os.getenv("PIPER_VOICE_ID", voice_id or _DEFAULT_VOICE),
        )
        self.english_voice_id = os.getenv("PIPER_VOICE_ID_EN", _DEFAULT_ENGLISH_VOICE)
        self.speaker_id = int(
            os.getenv("PIPER_SPEAKER_ID", str(speaker_id if speaker_id is not None else 0))
        )
        self.length_scale = float(
            os.getenv(
                "PIPER_LENGTH_SCALE",
                str(length_scale if length_scale is not None else 1.25),
            )
        )
        self.sentence_silence = float(
            os.getenv(
                "PIPER_SENTENCE_SILENCE",
                str(sentence_silence if sentence_silence is not None else 0.15),
            )
        )
        self.model_dir = Path(os.getenv("PIPER_MODEL_DIR", "/app/models/piper"))
        self._voice_cache: dict[str, PiperVoice] = {}
        self.sample_rate = _DEFAULT_SAMPLE_RATE

        for configured_voice_id in {self.nepali_voice_id, self.english_voice_id}:
            self._ensure_voice_assets(configured_voice_id)

        logger.info(
            "Loading Piper voices nepali=%s english=%s",
            self.nepali_voice_id,
            self.english_voice_id,
        )
        self._load_voice(self.nepali_voice_id)
        self._load_voice(self.english_voice_id)

    def _ensure_voice_assets(self, voice_id: str) -> None:
        voice_files = _VOICE_FILES.get(voice_id)
        if not voice_files:
            raise RuntimeError(f"Unsupported Piper voice id: {voice_id}")
        model_path = self.model_dir / voice_id / f"{voice_id}.onnx"
        config_path = self.model_dir / voice_id / f"{voice_id}.onnx.json"
        _download_if_missing(voice_files["model"], model_path)
        _download_if_missing(voice_files["config"], config_path)

    def _load_voice(self, voice_id: str):
        from piper import PiperVoice

        cached = self._voice_cache.get(voice_id)
        if cached is not None:
            return cached
        model_path = self.model_dir / voice_id / f"{voice_id}.onnx"
        config_path = self.model_dir / voice_id / f"{voice_id}.onnx.json"
        voice = PiperVoice.load(str(model_path), str(config_path))
        self._voice_cache[voice_id] = voice
        self.sample_rate = getattr(voice.config, "sample_rate", _DEFAULT_SAMPLE_RATE)
        return voice

    def _select_voice_id(self, text: str, language: str) -> str:
        language_key = (language or "").lower()
        if language_key.startswith("en"):
            return self.english_voice_id
        # If the text is pure ASCII latin (no Devanagari), treat as English
        if any("A" <= ch <= "z" for ch in text) and not any(
            "\u0900" <= ch <= "\u097F" for ch in text
        ):
            return self.english_voice_id
        return self.nepali_voice_id

    def synthesize(self, text: str, language: str = "ne") -> tuple[np.ndarray, int]:
        if not text.strip():
            return np.zeros(0, dtype=np.float32), self.sample_rate

        voice_id = self._select_voice_id(text, language)
        voice = self._load_voice(voice_id)

        wave_io = io.BytesIO()
        with wave.open(wave_io, "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)

        wave_io.seek(0)
        with wave.open(wave_io, "rb") as wav_file:
            frames = wav_file.readframes(wav_file.getnframes())
            sample_rate = wav_file.getframerate()

        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        return audio, sample_rate

    def health(self) -> bool:
        return bool(self._voice_cache)
