"""TTS router — Coqui XTTSv2 primary, Piper fallback.

Public interface is unchanged:
    service = TTSService(device="cuda:0")
    audio_array, sample_rate = service.synthesize(text, language)

Provider selection is controlled by TTS_PROVIDER env var:
    TTS_PROVIDER=coqui   → XTTSv2 primary + Piper fallback  (default)
    TTS_PROVIDER=piper   → Piper only (useful during rollout testing)
"""

from __future__ import annotations

import logging
import os

import numpy as np

from tts_provider import TTSProvider

logger = logging.getLogger("lipi.ml.tts")


class TTSService:
    """Route synthesis requests across TTS providers with automatic fallback."""

    def __init__(self, device: str = "cpu") -> None:
        provider_name = os.getenv("TTS_PROVIDER", "coqui").lower()
        self._primary: TTSProvider | None = None
        self._fallback: TTSProvider | None = None
        # Exposed so ml/main.py can report the effective sample rate
        self.sample_rate: int = 22_050

        # ── Primary: Coqui XTTSv2 ────────────────────────────────────────────
        if provider_name == "coqui":
            try:
                from tts_coqui import CoquiProvider

                self._primary = CoquiProvider(device=device)
                self._primary.warmup()
                self.sample_rate = getattr(self._primary, "_sample_rate", 24_000)
                logger.info("Primary TTS: Coqui XTTSv2 (device=%s)", device)
            except Exception as exc:
                logger.warning(
                    "Coqui XTTSv2 init failed (%s) — will use Piper only", exc
                )

        # ── Fallback: Piper ──────────────────────────────────────────────────
        # Always attempt to load Piper: it is the fallback when Coqui fails AND
        # the sole provider when TTS_PROVIDER=piper.
        try:
            from tts_piper import PiperProvider

            self._fallback = PiperProvider()
            if self._primary is None:
                # Piper is the effective primary — use its sample rate
                self.sample_rate = self._fallback.sample_rate
            logger.info(
                "Fallback TTS: Piper (ne=%s en=%s)",
                self._fallback.nepali_voice_id,
                self._fallback.english_voice_id,
            )
        except Exception as exc:
            logger.error("Piper init failed: %s", exc)

        # ── Startup summary ──────────────────────────────────────────────────
        if self._primary is not None and self._fallback is not None:
            logger.info("TTS stack: XTTSv2 → Piper fallback")
        elif self._primary is not None:
            logger.warning("TTS stack: XTTSv2 only (Piper unavailable)")
        elif self._fallback is not None:
            logger.info("TTS stack: Piper only (Coqui unavailable or TTS_PROVIDER=piper)")
        else:
            raise RuntimeError(
                "No TTS provider could be loaded. "
                "Check TTS_PROVIDER, model paths, and GPU availability."
            )

    # ── Public API (unchanged from previous Piper-only version) ──────────────

    def synthesize(self, text: str, language: str = "ne") -> tuple[np.ndarray, int]:
        """Synthesize text to audio.

        Tries primary provider first; on any exception falls back to Piper.
        Returns (float32 samples normalised to [-1, 1], sample_rate_hz).
        """
        if not text.strip():
            return np.zeros(0, dtype=np.float32), self.sample_rate

        if self._primary is not None:
            try:
                return self._primary.synthesize(text, language)
            except Exception as exc:
                logger.warning(
                    "Primary TTS (XTTSv2) failed for %d chars (%s) — falling back to Piper",
                    len(text),
                    exc,
                )

        if self._fallback is not None:
            return self._fallback.synthesize(text, language)

        raise RuntimeError("No TTS provider is available")

    # ── Introspection (used by ml/main.py /models/info) ──────────────────────

    @property
    def active_provider(self) -> str:
        if self._primary is not None:
            return "coqui_xttsv2"
        if self._fallback is not None:
            return "piper"
        return "none"

    @property
    def fallback_provider(self) -> str:
        return "piper" if self._fallback is not None else "none"
