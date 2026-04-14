"""LIPI Backend — FastAPI entrypoint."""

import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text, select

from cache import valkey
from config import settings
from db.connection import engine, SessionLocal
from models.points import TeacherPointsSummary
from routes import auth, sessions, leaderboard, teachers

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("lipi.backend")


async def _summary_rebuild_loop() -> None:
    """Rebuild all teacher point summaries every 5 minutes."""
    from services.points import rebuild_summary
    while True:
        await asyncio.sleep(300)
        try:
            async with SessionLocal() as db:
                rows = await db.execute(select(TeacherPointsSummary.teacher_id))
                user_ids = [r for (r,) in rows]
            for uid in user_ids:
                async with SessionLocal() as db:
                    await rebuild_summary(db, uid)
                    await db.commit()
            if user_ids:
                logger.debug("Summary rebuild complete for %d users", len(user_ids))
        except Exception as exc:
            logger.warning("Summary rebuild error: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("LIPI backend starting (env=%s)", settings.environment)

    # Initialize database schema
    from models.base import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized")

    app.state.http = httpx.AsyncClient(timeout=settings.ml_timeout)
    task = asyncio.create_task(_summary_rebuild_loop())
    yield
    logger.info("LIPI backend shutting down")
    task.cancel()
    await app.state.http.aclose()
    await valkey.aclose()
    await engine.dispose()


app = FastAPI(title="LIPI Backend", version="0.1.0", lifespan=lifespan)

# Parse comma-separated origins
allow_origins = [origin.strip() for origin in settings.app_url.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    environment: str
    database: bool
    valkey: bool
    vllm: bool
    ml_service: bool


async def _check_db() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("DB health check failed: %s", exc)
        return False


async def _check_valkey() -> bool:
    try:
        return bool(await valkey.ping())
    except Exception as exc:
        logger.warning("Valkey health check failed: %s", exc)
        return False


async def _check_http(url: str) -> bool:
    try:
        r = await app.state.http.get(url, timeout=2.0)
        return r.status_code < 500
    except Exception:
        return False


app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(leaderboard.router)
app.include_router(teachers.router)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    db_ok = await _check_db()
    vk_ok = await _check_valkey()
    vllm_ok = await _check_http(f"{settings.vllm_url}/v1/models")
    ml_ok = await _check_http(f"{settings.ml_service_url}/health")

    all_ok = all([db_ok, vk_ok, vllm_ok, ml_ok])
    return HealthResponse(
        status="ok" if all_ok else "degraded",
        environment=settings.environment,
        database=db_ok,
        valkey=vk_ok,
        vllm=vllm_ok,
        ml_service=ml_ok,
    )


@app.get("/")
async def root() -> dict:
    return {"service": "lipi-backend", "version": "0.1.0"}
