"""Abstract TTS provider interface for LIPI ML service."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class TTSProvider(ABC):
    """Common contract for all TTS backends (Piper, Coqui XTTSv2, …)."""

    @abstractmethod
    def synthesize(self, text: str, language: str = "ne") -> tuple[np.ndarray, int]:
        """Return (audio_samples_float32, sample_rate_hz)."""
        ...

    @abstractmethod
    def health(self) -> bool:
        """Return True if the provider is ready to synthesize."""
        ...

    def warmup(self) -> None:
        """Optional: synthesize a short phrase to warm up the model."""
