"""
FastAPI Main Application initialization, CORS middleware, static file mounting, and routes.
"""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import router as api_router
from app.config import settings
from utils.logger import logger

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(
    title=settings.app_name,
    description="Production-quality RAG-powered AI Technical Interview Agent",
    version=settings.version,
)

# CORS Middleware Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Frontend Static Files if directory exists
frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists() and frontend_dir.is_dir():
    app.mount("/frontend", StaticFiles(directory=str(frontend_dir)), name="frontend")


@app.get("/", summary="Root Endpoint Serving Frontend")
def root():
    """Serves the frontend interface index.html at root URL."""
    index_file = BASE_DIR / "frontend" / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "message": "AI Interview Agent API is running.",
        "docs": "/docs",
    }


@app.get("/health", summary="Application Health Check")
def health():
    """Returns application health and configuration status."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.version,
        "llm_model": settings.llm_model_name,
        "vector_db": settings.vector_db_type,
    }


# Include API Router
try:
    app.include_router(api_router)
    logger.info("Successfully registered api_router on FastAPI application.")
except Exception as exc:
    logger.error(f"Failed to register api_router: {exc}", exc_info=True)
    raise


# Print all registered routes on startup (Requirement 5)
@app.on_event("startup")
def print_registered_routes():
    logger.info("==================================================")
    logger.info(" Registered FastAPI Application Routes:")
    for route in app.routes:
        if not hasattr(route, "path"):
            continue
        methods = getattr(route, "methods", None)
        methods_str = ", ".join(sorted(methods)) if methods else "MOUNT"
        logger.info(f"  -> {route.path} [{methods_str}]")
    logger.info("==================================================")
