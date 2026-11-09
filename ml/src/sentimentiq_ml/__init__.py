"""Public data contracts, baseline inference, and analytics."""

from .analytics import compute_analytics
from .engine import SentimentEngine, analyze, analyze_batch, get_model_info
from .types import (
    AnalysisError, AnalysisResult, AnalyticsSummary, AspectAnalytics,
    AspectResult, BatchOutcome, ConfidenceAggregate, ModelInfo, Sentiment,
    StoredAspect, StoredResult,
)

__all__ = [
    "AnalysisError", "AnalysisResult", "AnalyticsSummary", "AspectAnalytics",
    "AspectResult", "BatchOutcome", "ConfidenceAggregate", "ModelInfo",
    "Sentiment", "SentimentEngine", "StoredAspect", "StoredResult",
    "analyze", "analyze_batch", "compute_analytics", "get_model_info",
]
