"""
LIPI ML Service — STT (faster-whisper) + TTS (mms-tts-npi)
Runs on GPUs 0 and 1, sharing memory with vLLM.
"""

import io
import logging
import os
from contextlib import asynccontextmanager

import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from stt import STTService
from tts import TTSService

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("lipi.ml")

# ─── Service instances ──────────────────────────────────────────────────────
stt_service: STTService | None = None
tts_service: TTSService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models on startup, free on shutdown."""
    global stt_service, tts_service

    logger.info("Loading STT model (faster-whisper large-v3)...")
    stt_service = STTService(device=os.getenv("STT_DEVICE", "cuda:0"))
    logger.info("STT loaded")

    logger.info("Loading TTS model (facebook/mms-tts-npi)...")
    tts_service = TTSService(device=os.getenv("TTS_DEVICE", "cuda:1"))
    logger.info("TTS loaded")

    yield

    logger.info("Shutting down ML service")
    stt_service = None
    tts_service = None
    torch.cuda.empty_cache()


app = FastAPI(title="LIPI ML Service", version="0.1.0", lifespan=lifespan)


# ─── Schemas ────────────────────────────────────────────────────────────────
class STTResponse(BaseModel):
    text: str
    language: str
    confidence: float
    duration_ms: int


class TTSRequest(BaseModel):
    text: str
    language: str = "ne"


class HealthResponse(BaseModel):
    status: str
    cuda_available: bool
    stt_loaded: bool
    tts_loaded: bool
    gpu_count: int


# ─── Endpoints ──────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok" if (stt_service and tts_service) else "loading",
        cuda_available=torch.cuda.is_available(),
        stt_loaded=stt_service is not None,
        tts_loaded=tts_service is not None,
        gpu_count=torch.cuda.device_count(),
    )


@app.post("/stt", response_model=STTResponse)
async def speech_to_text(audio: UploadFile = File(...)) -> STTResponse:
    """Transcribe an audio file. Accepts wav/mp3/ogg/webm."""
    if stt_service is None:
        raise HTTPException(status_code=503, detail="STT service not ready")

    audio_bytes = await audio.read()
    try:
        result = stt_service.transcribe(audio_bytes)
        return STTResponse(**result)
    except Exception as exc:
        logger.exception("STT failed")
        raise HTTPException(status_code=500, detail=f"STT failed: {exc}")


@app.post("/tts")
async def text_to_speech(request: TTSRequest) -> Response:
    """Synthesize speech from text. Returns WAV audio bytes."""
    if tts_service is None:
        raise HTTPException(status_code=503, detail="TTS service not ready")

    try:
        audio_array, sample_rate = tts_service.synthesize(
            text=request.text,
            language=request.language,
        )
        buffer = io.BytesIO()
        sf.write(buffer, audio_array, sample_rate, format="WAV")
        return Response(
            content=buffer.getvalue(),
            media_type="audio/wav",
            headers={"X-Sample-Rate": str(sample_rate)},
        )
    except Exception as exc:
        logger.exception("TTS failed")
        raise HTTPException(status_code=500, detail=f"TTS failed: {exc}")


@app.get("/models/info")
async def models_info() -> dict:
    return {
        "stt": {
            "model": "faster-whisper large-v3",
            "device": os.getenv("STT_DEVICE", "cuda:0"),
            "loaded": stt_service is not None,
        },
        "tts": {
            "model": "facebook/mms-tts-npi",
            "device": os.getenv("TTS_DEVICE", "cuda:1"),
            "loaded": tts_service is not None,
        },
    }
