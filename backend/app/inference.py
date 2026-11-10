"""Synchronous inference routes backed by sentimentiq_ml."""

from __future__ import annotations

import logging
from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from sentimentiq_ml import analyze, analyze_batch
from sentimentiq_ml.types import AnalysisResult

from .schemas import (
    AnalysisRequest,
    AnalysisResponse,
    AspectResponse,
    BatchAnalysisRequest,
    BatchOutcomeResponse,
    SentimentResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["inference"])


def _analysis_response(result: AnalysisResult) -> AnalysisResponse:
    values = asdict(result)
    return AnalysisResponse(
        overall=SentimentResponse(**values["overall"]),
        aspects=[AspectResponse(**aspect) for aspect in values["aspects"]],
    )


@router.post("/analyze", response_model=AnalysisResponse)
def analyze_review(request: AnalysisRequest) -> AnalysisResponse:
    """Analyze one review without persisting the result."""
    try:
        result = analyze(request.text, request.domain)
        return _analysis_response(result)
    except Exception as exc:
        logger.exception("Inference failed for a single review")
        raise HTTPException(status_code=500, detail="Analysis could not be completed.") from exc


@router.post("/analyze/batch", response_model=list[BatchOutcomeResponse])
def analyze_reviews(request: BatchAnalysisRequest) -> list[BatchOutcomeResponse]:
    """Analyze an ordered batch without persisting the results."""
    try:
        outcomes = analyze_batch(request.texts, request.domain)
        return [
            BatchOutcomeResponse(
                input_index=outcome.input_index,
                status="succeeded" if outcome.result is not None else "failed",
                result=(
                    _analysis_response(outcome.result)
                    if outcome.result is not None
                    else None
                ),
                error=(asdict(outcome.error) if outcome.error is not None else None),
            )
            for outcome in outcomes
        ]
    except Exception as exc:
        logger.exception("Inference failed for a batch")
        raise HTTPException(status_code=500, detail="Batch analysis could not be completed.") from exc
