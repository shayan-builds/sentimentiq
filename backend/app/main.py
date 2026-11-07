"""FastAPI application entry point for SentimentIQ."""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

app = FastAPI(
    title="SentimentIQ API",
    description="API foundation for sentiment and aspect analysis.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
def database_health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    """Check that the application can run a simple database query."""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
