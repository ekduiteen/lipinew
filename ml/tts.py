"""TTS service — facebook/mms-tts-npi (Nepali) via transformers VITS."""

import logging

import numpy as np
import torch
from transformers import VitsModel, AutoTokenizer

logger = logging.getLogger("lipi.ml.tts")


class TTSService:
    """Wraps facebook/mms-tts-npi for Nepali speech synthesis."""

    def __init__(self, device: str = "cuda:1", model_id: str = "facebook/mms-tts-npi"):
        self.device = device
        logger.info("Loading TTS %s on %s", model_id, device)

        self.model = VitsModel.from_pretrained(model_id).to(device)
        self.model.eval()
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.sample_rate = self.model.config.sampling_rate

    @torch.inference_mode()
    def synthesize(self, text: str, language: str = "ne") -> tuple[np.ndarray, int]:
        """Synthesize text to a float32 mono waveform."""
        if not text.strip():
            return np.zeros(0, dtype=np.float32), self.sample_rate

        inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
        output = self.model(**inputs).waveform  # (1, T)
        audio = output.squeeze(0).cpu().numpy().astype(np.float32)
        return audio, self.sample_rate
