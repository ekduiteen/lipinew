"""LIPI ML service - eager-loaded STT, TTS, and speaker embedding for async learning."""

from __future__ import annotations

import io
import logging
import os
from contextlib import asynccontextmanager

import soundfile as sf
import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from speaker_embed import SpeakerEmbeddingService
from stt import STTService
from tts import TTSService

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("lipi.ml")

stt_service: STTService | None = None
tts_service: TTSService | None = None
speaker_embed_service: SpeakerEmbeddingService | None = None
stt_error: str | None = None
tts_error: str | None = None
speaker_embed_error: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load required models at startup so the first voice turn is hot."""
    global stt_service, tts_service, speaker_embed_service
    global stt_error, tts_error, speaker_embed_error

    stt_service = None
    tts_service = None
    speaker_embed_service = None
    stt_error = None
    tts_error = None
    speaker_embed_error = None

    try:
        logger.info("Loading STT model (faster-whisper large-v3)...")
        stt_service = STTService(device=os.getenv("STT_DEVICE", "cuda:0"))
        logger.info("STT loaded")
    except Exception as exc:
        stt_error = str(exc)
        logger.exception("STT startup failed")

    try:
        provider = os.getenv("TTS_PROVIDER", "piper")
        logger.info("Loading TTS (provider=%s)...", provider)
        tts_service = TTSService(device=os.getenv("TTS_DEVICE", "cuda:0"))
        logger.info("TTS loaded (active=%s fallback=%s)", tts_service.active_provider, tts_service.fallback_provider)
    except Exception as exc:
        tts_error = str(exc)
        logger.exception("TTS startup failed")

    try:
        logger.info("Loading speaker embedding service...")
        speaker_embed_service = SpeakerEmbeddingService()
        logger.info("Speaker embedding service loaded")
    except Exception as exc:
        speaker_embed_error = str(exc)
        logger.exception("Speaker embedding startup failed")

    # STT and TTS are required; speaker embeddings are optional (async learning only)
    if stt_service is None or tts_service is None:
        raise RuntimeError(
            "ML service failed to load required models: "
            f"stt_error={stt_error!r} tts_error={tts_error!r}"
        )
    if speaker_embed_service is None:
        logger.warning("Speaker embedding service unavailable — proceeding in degraded mode: %s", speaker_embed_error)

    yield

    logger.info("Shutting down ML service")
    stt_service = None
    tts_service = None
    speaker_embed_service = None
    torch.cuda.empty_cache()


app = FastAPI(title="LIPI ML Service", version="0.3.0", lifespan=lifespan)


class STTResponse(BaseModel):
    text: str
    language: str
    confidence: float
    duration_ms: int


class TTSRequest(BaseModel):
    text: str
    language: str = "ne"


class SpeakerEmbedResponse(BaseModel):
    embedding: list[float]
    dimensions: int
    duration_ms: int
    quality: str
    latency_ms: int
    model: str


class HealthResponse(BaseModel):
    status: str
    cuda_available: bool
    stt_loaded: bool
    tts_loaded: bool
    speaker_embed_loaded: bool
    gpu_count: int
    stt_error: str | None = None
    tts_error: str | None = None
    speaker_embed_error: str | None = None


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    all_ok = stt_service is not None and tts_service is not None and speaker_embed_service is not None
    return HealthResponse(
        status="ok" if all_ok else "degraded",
        cuda_available=torch.cuda.is_available(),
        stt_loaded=stt_service is not None,
        tts_loaded=tts_service is not None,
        speaker_embed_loaded=speaker_embed_service is not None,
        gpu_count=torch.cuda.device_count(),
        stt_error=stt_error,
        tts_error=tts_error,
        speaker_embed_error=speaker_embed_error,
    )


@app.post("/stt", response_model=STTResponse)
async def speech_to_text(
    audio: UploadFile = File(...),
    prompt: str = Form(""),
    language_hint: str = Form(""),
) -> STTResponse:
    if stt_service is None:
        raise HTTPException(status_code=503, detail=f"STT service not ready: {stt_error or 'unknown error'}")

    audio_bytes = await audio.read()
    try:
        result = stt_service.transcribe(
            audio_bytes,
            prompt=prompt.strip() or None,
            language_hint=language_hint.strip() or None,
        )
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


@app.post("/speaker-embed", response_model=SpeakerEmbedResponse)
async def speaker_embed(audio: UploadFile = File(...)) -> SpeakerEmbedResponse:
    if speaker_embed_service is None:
        raise HTTPException(status_code=503, detail=f"Speaker embedding service not ready: {speaker_embed_error or 'unknown error'}")

    audio_bytes = await audio.read()
    try:
        result = speaker_embed_service.embed_audio_bytes(audio_bytes)
        return SpeakerEmbedResponse(**result)
    except Exception as exc:
        logger.exception("Speaker embedding failed")
        raise HTTPException(status_code=500, detail=f"Speaker embedding failed: {exc}")


@app.get("/models/info")
async def models_info() -> dict:
    tts_info: dict = {
        "provider": os.getenv("TTS_PROVIDER", "coqui"),
        "loaded": tts_service is not None,
        "error": tts_error,
    }
    if tts_service is not None:
        tts_info["active_provider"] = tts_service.active_provider
        tts_info["fallback_provider"] = tts_service.fallback_provider
        tts_info["sample_rate"] = tts_service.sample_rate
    if os.getenv("TTS_PROVIDER", "coqui") == "coqui":
        tts_info["xtts_model"] = os.getenv("XTTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")
        tts_info["xtts_speaker"] = os.getenv("XTTS_SPEAKER", "Claribel Dervla")
        tts_info["xtts_reference_wav"] = os.getenv("XTTS_REFERENCE_WAV", "")
    tts_info["piper_voice_ne"] = os.getenv("PIPER_VOICE_ID_NE", os.getenv("PIPER_VOICE_ID", "ne_NP-google-medium"))
    tts_info["piper_voice_en"] = os.getenv("PIPER_VOICE_ID_EN", "en_US-lessac-medium")

    return {
        "stt": {
            "model": "faster-whisper large-v3",
            "device": os.getenv("STT_DEVICE", "cuda:0"),
            "loaded": stt_service is not None,
            "error": stt_error,
        },
        "speaker_embed": {
            "model": "acoustic_signature_v1",
            "loaded": speaker_embed_service is not None,
            "error": speaker_embed_error,
            "dimensions": 512,
        },
        "tts": tts_info,
    }
