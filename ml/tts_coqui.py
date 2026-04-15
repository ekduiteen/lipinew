"""Coqui XTTSv2 TTS provider — primary voice for LIPI.

XTTSv2 officially supports: en es fr de it pt pl tr ru nl cs ar zh-cn ja hu ko hi
Nepali is NOT in that list. We map ne/new → hi (Hindi) which shares Devanagari
script and phonetic patterns. It sounds close but is not native Nepali.
Piper (ne_NP-google-medium) remains available as a language-accurate fallback.

Voice cloning: set XTTS_REFERENCE_WAV to a path of a 6-30 second clean speech
WAV to activate speaker cloning. Leave empty to use the built-in speaker.
"""

from __future__ import annotations

import logging
import os

import numpy as np

from tts_provider import TTSProvider

logger = logging.getLogger("lipi.ml.tts_coqui")

# Mapping from LIPI language codes → XTTSv2 language codes
_XTTS_LANG: dict[str, str] = {
    "ne": "hi",       # Nepali → Hindi (closest Devanagari, XTTSv2 limitation)
    "new": "hi",      # Newari
    "newari": "hi",
    "nepali": "hi",
    "ne_np": "hi",
    "hi": "hi",
    "hindi": "hi",
    "en": "en",
    "en_us": "en",
    "english": "en",
    "mixed": "en",    # mixed turns default to English for clarity
}

# XTTSv2 generates audio at 24 kHz
_SAMPLE_RATE = 24_000

# XTTSv2 degrades above ~350 chars; response_cleanup already limits to 28 words
# but keep a hard ceiling here as a safety net
_MAX_CHARS = 350

# Built-in XTTSv2 speakers (run tts.speakers to see full list)
_DEFAULT_SPEAKER = "Claribel Dervla"


class CoquiProvider(TTSProvider):
    """Coqui XTTSv2 — expressive multilingual voice, GPU-accelerated."""

    def __init__(self, device: str = "cuda") -> None:
        import torch
        from TTS.api import TTS as CoquiTTS  # pip install TTS

        # Resolve device: env var overrides constructor arg; fall back to CPU
        resolved = os.getenv("TTS_DEVICE", device)
        if resolved.startswith("cuda") and not torch.cuda.is_available():
            logger.warning("CUDA not available — loading XTTSv2 on CPU (expect slow synthesis)")
            resolved = "cpu"
        self._device = resolved

        model_name = os.getenv(
            "XTTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2"
        )
        self._speaker: str = os.getenv("XTTS_SPEAKER", _DEFAULT_SPEAKER)
        self._reference_wav: str = os.getenv("XTTS_REFERENCE_WAV", "")
        self._sample_rate = _SAMPLE_RATE

        logger.info(
            "Loading Coqui XTTSv2 (model=%s device=%s speaker=%s)…",
            model_name,
            self._device,
            self._speaker if not self._reference_wav else "voice-cloning",
        )
        self._tts = CoquiTTS(model_name).to(self._device)
        logger.info("Coqui XTTSv2 loaded")

    # ── public API ────────────────────────────────────────────────────────────

    def synthesize(self, text: str, language: str = "ne") -> tuple[np.ndarray, int]:
        if not text.strip():
            return np.zeros(0, dtype=np.float32), self._sample_rate

        text = text.strip()[:_MAX_CHARS]
        xtts_lang = _XTTS_LANG.get(language.lower(), "en")

        if self._reference_wav:
            wav = self._tts.tts(
                text=text,
                speaker_wav=self._reference_wav,
                language=xtts_lang,
            )
        else:
            wav = self._tts.tts(
                text=text,
                speaker=self._speaker,
                language=xtts_lang,
            )

        return np.array(wav, dtype=np.float32), self._sample_rate

    def health(self) -> bool:
        return self._tts is not None

    def warmup(self) -> None:
        """Synthesize a short phrase so the first real turn is instant."""
        try:
            logger.info("Warming up XTTSv2…")
            self.synthesize("नमस्ते।", language="ne")
            logger.info("XTTSv2 warmup done")
        except Exception as exc:
            # Warmup failure is non-fatal — the first real turn will be slower
            logger.warning("XTTSv2 warmup failed (non-fatal): %s", exc)
