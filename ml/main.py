"""LIPI ML service - eager-loaded STT and TTS for hot voice turns."""

from __future__ import annotations

import io
import logging
import os
from contextlib import asynccontextmanager

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

stt_service: STTService | None = None
tts_service: TTSService | None = None
stt_error: str | None = None
tts_error: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load both models at startup so the first voice turn is hot."""
    global stt_service, tts_service, stt_error, tts_error

    stt_service = None
    tts_service = None
    stt_error = None
    tts_error = None

    try:
        logger.info("Loading STT model (faster-whisper large-v3)...")
        stt_service = STTService(device=os.getenv("STT_DEVICE", "cuda:0"))
        logger.info("STT loaded")
    except Exception as exc:
        stt_error = str(exc)
        logger.exception("STT startup failed")

    try:
        logger.info("Loading TTS model (Piper)...")
        tts_service = TTSService(device=os.getenv("TTS_DEVICE", "cuda:0"))
        logger.info("TTS loaded")
    except Exception as exc:
        tts_error = str(exc)
        logger.exception("TTS startup failed")

    if stt_service is None or tts_service is None:
        raise RuntimeError(
            "ML service failed to hot-load required models: "
            f"stt_error={stt_error!r} tts_error={tts_error!r}"
        )

    yield

    logger.info("Shutting down ML service")
    stt_service = None
    tts_service = None
    torch.cuda.empty_cache()


app = FastAPI(title="LIPI ML Service", version="0.2.0", lifespan=lifespan)


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
    stt_error: str | None = None
    tts_error: str | None = None


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    all_ok = stt_service is not None and tts_service is not None
    return HealthResponse(
        status="ok" if all_ok else "degraded",
        cuda_available=torch.cuda.is_available(),
        stt_loaded=stt_service is not None,
        tts_loaded=tts_service is not None,
        gpu_count=torch.cuda.device_count(),
        stt_error=stt_error,
        tts_error=tts_error,
    )


@app.post("/stt", response_model=STTResponse)
async def speech_to_text(audio: UploadFile = File(...)) -> STTResponse:
    if stt_service is None:
        raise HTTPException(status_code=503, detail=f"STT service not ready: {stt_error or 'unknown error'}")

    audio_bytes = await audio.read()
    try:
        result = stt_service.transcribe(audio_bytes)
        return STTResponse(**result)
    except Exception as exc:
        logger.exception("STT failed")
        raise HTTPException(status_code=500, detail=f"STT failed: {exc}")


@app.post("/tts")
async def text_to_speech(request: TTSRequest) -> Response:
    if tts_service is None:
        raise HTTPException(status_code=503, detail=f"TTS service not ready: {tts_error or 'unknown error'}")

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
            "error": stt_error,
        },
        "tts": {
            "model": "piper",
            "device": "cpu",
            "loaded": tts_service is not None,
            "error": tts_error,
            "voice_id": os.getenv("PIPER_VOICE_ID", "ne_NP-google-medium"),
            "length_scale": float(os.getenv("PIPER_LENGTH_SCALE", "1.25")),
            "sentence_silence": float(os.getenv("PIPER_SENTENCE_SILENCE", "0.15")),
        },
    }
