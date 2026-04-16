"""LIPI Backend — FastAPI entrypoint."""

import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text, select
from urllib.parse import urlsplit, urlunsplit
from slowapi.errors import RateLimitExceeded
from rate_limit import limiter

from cache import valkey
from config import settings
from db.connection import engine, SessionLocal
from models.points import TeacherPointsSummary
import models.phrases  # Load phrase laboratory models
from routes import auth, sessions, leaderboard, teachers, dashboard, phrases
from services import learning as learning_svc

try:
    import models.heritage  # type: ignore[import-not-found]  # Load heritage models
    from routes import heritage
except ModuleNotFoundError:
    heritage = None

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

    summary_task = None
    learning_task = None

    try:
        # Validate JWT_SECRET is securely configured (defensive check)
        if not settings.jwt_secret or len(settings.jwt_secret) < 32:
            raise RuntimeError(
                "JWT_SECRET is not securely configured. "
                "Set JWT_SECRET env var to a 32+ character random string."
            )
        logger.debug("JWT_SECRET validation passed")

        # Validate Valkey is reachable before serving traffic
        try:
            await valkey.ping()
            logger.info("Valkey reachable")
        except Exception as exc:
            logger.warning("Valkey unhealthy at startup: %s", exc)

        # Initialize HTTP client for async requests
        app.state.http = httpx.AsyncClient(timeout=settings.ml_timeout)

        # Start background tasks
        summary_task = asyncio.create_task(_summary_rebuild_loop())
        learning_task = asyncio.create_task(learning_svc.run_worker(app.state.http))

        logger.info("LIPI backend startup complete - ready for requests")
    except Exception as exc:
        logger.error("Fatal error during startup: %s", exc, exc_info=True)
        raise

    try:
        yield
    finally:
        logger.info("LIPI backend shutting down")
        if summary_task:
            summary_task.cancel()
        if learning_task:
            learning_task.cancel()
        try:
            await app.state.http.aclose()
        except (AttributeError, NameError):
            pass
        try:
            await valkey.aclose()
        except Exception:
            pass
        try:
            await engine.dispose()
        except Exception:
            pass


app = FastAPI(title="LIPI Backend", version="0.1.0", lifespan=lifespan)

# ─── Rate Limiting ───────────────────────────────────────────────────────────────
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors."""
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )


def _expand_local_origins(raw_origins: str) -> list[str]:
    origins: list[str] = []
    for origin in raw_origins.split(","):
        origin = origin.strip()
        if not origin:
            continue
        origins.append(origin)
        parsed = urlsplit(origin)
        if parsed.hostname == "localhost":
            origins.append(urlunsplit((parsed.scheme, f"127.0.0.1:{parsed.port}" if parsed.port else "127.0.0.1", parsed.path, parsed.query, parsed.fragment)))
        elif parsed.hostname == "127.0.0.1":
            origins.append(urlunsplit((parsed.scheme, f"localhost:{parsed.port}" if parsed.port else "localhost", parsed.path, parsed.query, parsed.fragment)))
    # Preserve order while dropping duplicates
    return list(dict.fromkeys(origins))


allow_origins = _expand_local_origins(settings.app_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# ─── Request Size Limit Middleware ───────────────────────────────────────────
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

_MAX_UPLOAD_BYTES = 100_000_000  # 100 MB


class _LimitUploadSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH"):
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > _MAX_UPLOAD_BYTES:
                return StarletteResponse("Payload too large", status_code=413)
        return await call_next(request)


app.add_middleware(_LimitUploadSizeMiddleware)


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
app.include_router(dashboard.router)
app.include_router(phrases.router)
if heritage is not None:
    app.include_router(heritage.router)
else:
    logger.warning("Heritage routes disabled: models.heritage module is missing")

# ─── Rate limiting config ─────────────────────────────────────────────────────
# The limiter is registered and exception handler set up above
# Specific endpoints use the @limiter.limit() decorator (defined in route files)
app.limiter = limiter  # Make limiter available to routes


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
