"""Lightweight speaker/acoustic embedding extraction for async dialect capture."""

from __future__ import annotations

import io
import math
import time

import numpy as np
import soundfile as sf
import torch
import torchaudio


class SpeakerEmbeddingService:
    """Deterministic 512-d acoustic signature for teacher-turn comparison and clustering.

    This is intentionally async-worker-only. It is not used in the live reply path.
    """

    def __init__(self, sample_rate: int = 16000, embedding_dim: int = 512):
        self.sample_rate = sample_rate
        self.embedding_dim = embedding_dim
        self.mel = torchaudio.transforms.MelSpectrogram(
            sample_rate=sample_rate,
            n_fft=400,
            hop_length=160,
            n_mels=80,
        )

    def embed_audio_bytes(self, audio_bytes: bytes) -> dict:
        start = time.perf_counter()
        waveform, sample_rate = sf.read(io.BytesIO(audio_bytes), dtype="float32")
        if waveform.ndim > 1:
            waveform = waveform.mean(axis=1)
        if waveform.size == 0:
            raise ValueError("empty audio")

        waveform_t = torch.from_numpy(waveform)
        if sample_rate != self.sample_rate:
            waveform_t = torchaudio.functional.resample(waveform_t, sample_rate, self.sample_rate)

        duration_ms = int((waveform_t.numel() / self.sample_rate) * 1000)
        if duration_ms < 800:
            raise ValueError("audio too short for speaker embedding")

        mel = self.mel(waveform_t).clamp_min(1e-5).log()
        delta = mel[:, 1:] - mel[:, :-1]

        features = [
            mel.mean(dim=1),
            mel.std(dim=1),
            delta.mean(dim=1),
            delta.std(dim=1),
        ]

        rms = torch.sqrt(torch.mean(waveform_t ** 2))
        zero_crossings = torch.mean((waveform_t[:-1] * waveform_t[1:] < 0).float()) if waveform_t.numel() > 1 else torch.tensor(0.0)
        energy = mel.mean()
        extras = torch.tensor(
            [
                float(rms),
                float(zero_crossings),
                float(energy),
                float(torch.max(torch.abs(waveform_t))),
            ],
            dtype=torch.float32,
        )

        signature = torch.cat(features + [extras], dim=0)
        repeated = signature.repeat(math.ceil(self.embedding_dim / signature.numel()))[: self.embedding_dim]
        embedding = torch.nn.functional.normalize(repeated, dim=0).cpu().tolist()

        return {
            "embedding": embedding,
            "dimensions": self.embedding_dim,
            "duration_ms": duration_ms,
            "quality": "good" if duration_ms >= 1400 else "usable",
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "model": "acoustic_signature_v1",
        }
