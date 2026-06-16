"""
FastAPI application entry point.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db.database import create_db_and_tables
from app.api.routes import router
from app.api.websocket import ws_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown events."""
    settings = get_settings()

    # Startup
    logger.info("=" * 60)
    logger.info("🎬 AI Job Reel Generator — Starting up")
    logger.info(f"   Environment: {settings.app_env.value}")
    logger.info(f"   Database: {settings.database_url}")
    logger.info(f"   Redis: {settings.redis_url}")
    logger.info("=" * 60)

    # Create storage directories
    settings.ensure_storage_dirs()

    # Create database tables
    create_db_and_tables()

    # Log provider availability
    from app.config import LLMProvider, VoiceProvider, VideoProvider
    for p in LLMProvider:
        status = "✅" if settings.has_llm_provider(p) else "❌"
        logger.info(f"   LLM {p.value}: {status}")
    for p in VoiceProvider:
        status = "✅" if settings.has_voice_provider(p) else "❌"
        logger.info(f"   Voice {p.value}: {status}")
    for p in VideoProvider:
        status = "✅" if settings.has_video_provider(p) else "❌"
        logger.info(f"   Video {p.value}: {status}")

    logger.info("🚀 Server ready!")

    yield

    # Shutdown
    logger.info("👋 Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="AI Job Reel Generator",
    description="Production-grade system for generating faceless job opportunity reels with AI voiceover, captions, and B-roll visuals.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware — allow frontend in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount storage for serving generated files
settings = get_settings()
settings.ensure_storage_dirs()
app.mount("/storage", StaticFiles(directory=str(settings.storage_dir)), name="storage")

# Register routers
app.include_router(router)
app.include_router(ws_router)


@app.get("/")
async def root():
    return {
        "name": "AI Job Reel Generator",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
