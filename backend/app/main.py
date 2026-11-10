"""FastAPI application entry point for SentimentIQ."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from sentimentiq_ml import get_model_info

from .database import get_db
from .inference import router as inference_router


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Load and identify the product model once for each worker."""
    artifact = os.environ.get("SENTIMENTIQ_MODEL_PATH")
    if not artifact:
        raise RuntimeError(
            "SENTIMENTIQ_MODEL_PATH must point to the trained product model artifact."
        )
    artifact_path = Path(artifact)
    if not artifact_path.is_file():
        raise RuntimeError(
            f"SENTIMENTIQ_MODEL_PATH does not point to an existing file: {artifact_path}"
        )
    try:
        application.state.product_model_info = get_model_info("product")
    except Exception as exc:
        raise RuntimeError(
            "Could not initialize the product model configured by SENTIMENTIQ_MODEL_PATH."
        ) from exc
    yield

app = FastAPI(
    title="SentimentIQ API",
    description="API foundation for sentiment and aspect analysis.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(inference_router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
def database_health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    """Check that the application can run a simple database query."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
