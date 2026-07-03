from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.config import settings
from app.core.logging import setup_logging
from app.core.rate_limit import limiter
from app.routers import (
    auth_router,
    matches_router,
    predictions_router,
    leaderboard_router,
    matchdays_router,
    stats_router,
    config_router,
)
from app.services.scheduler import start_scheduler, stop_scheduler
from app.services.football_api import close_client
import logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Mundial Quiniela API iniciando...")
    start_scheduler()
    yield
    stop_scheduler()
    await close_client()
    logger.info("Mundial Quiniela API detenida.")


app = FastAPI(
    title="Mundial Quiniela API",
    description="API para la quiniela del Mundial FIFA 2026",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    # Mínimo privilegio: solo los métodos/cabeceras que la SPA usa de verdad
    # (GET/POST/DELETE + preflight OPTIONS; Authorization para el JWT).
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Rutas
app.include_router(auth_router,        prefix="/api")
app.include_router(matches_router,     prefix="/api")
app.include_router(predictions_router, prefix="/api")
app.include_router(leaderboard_router, prefix="/api")
app.include_router(matchdays_router,   prefix="/api")
app.include_router(stats_router,       prefix="/api")
app.include_router(config_router,      prefix="/api")


@app.get("/", tags=["Health"])
async def root():
    return {
        "app":     "Mundial Quiniela API",
        "version": settings.APP_VERSION,
        "status":  "running",
        "docs":    "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
