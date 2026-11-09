"""Typed contracts shared by the ML component and platform backend."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Literal

Domain = Literal["product", "campus"]
SentimentLabel = Literal["positive", "negative", "neutral", "mixed"]
ConfidenceKind = Literal["raw_score", "calibrated_probability"]

SENTIMENT_LABELS: tuple[SentimentLabel, ...] = (
    "positive", "negative", "neutral", "mixed",
)
CONFIDENCE_KINDS: tuple[ConfidenceKind, ...] = (
    "raw_score", "calibrated_probability",
)


def _validate_sentiment(
    sentiment_label: str,
    sentiment_score: float,
    confidence_value: float,
    confidence_kind: str,
) -> None:
    if sentiment_label not in SENTIMENT_LABELS:
        raise ValueError("unsupported sentiment_label")
    if confidence_kind not in CONFIDENCE_KINDS:
        raise ValueError("unsupported confidence_kind")
    if not isfinite(sentiment_score) or not -1.0 <= sentiment_score <= 1.0:
        raise ValueError("sentiment_score must be finite and between -1.0 and 1.0")
    if not isfinite(confidence_value) or not 0.0 <= confidence_value <= 1.0:
        raise ValueError("confidence_value must be finite and between 0.0 and 1.0")


@dataclass(frozen=True, slots=True)
class Sentiment:
    sentiment_label: SentimentLabel
    sentiment_score: float
    confidence_value: float
    confidence_kind: ConfidenceKind

    def __post_init__(self) -> None:
        _validate_sentiment(
            self.sentiment_label,
            self.sentiment_score,
            self.confidence_value,
            self.confidence_kind,
        )


@dataclass(frozen=True, slots=True)
class AspectResult:
    aspect_text: str
    sentiment_label: SentimentLabel
    sentiment_score: float
    confidence_value: float
    confidence_kind: ConfidenceKind
    aspect_category: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None

    def __post_init__(self) -> None:
        _validate_sentiment(
            self.sentiment_label,
            self.sentiment_score,
            self.confidence_value,
            self.confidence_kind,
        )
        if not self.aspect_text:
            raise ValueError("aspect_text must not be empty")
        if (self.start_offset is None) != (self.end_offset is None):
            raise ValueError("start_offset and end_offset must both be set or both be null")
        if self.start_offset is not None:
            if self.start_offset < 0 or self.end_offset is None or self.end_offset <= self.start_offset:
                raise ValueError("offsets must be nonnegative and end_offset must exceed start_offset")


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    overall: Sentiment
    aspects: tuple[AspectResult, ...] = ()


@dataclass(frozen=True, slots=True)
class AnalysisError:
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class BatchOutcome:
    input_index: int
    result: AnalysisResult | None = None
    error: AnalysisError | None = None

    def __post_init__(self) -> None:
        if self.input_index < 0:
            raise ValueError("input_index must be nonnegative")
        if (self.result is None) == (self.error is None):
            raise ValueError("exactly one of result or error must be set")


@dataclass(frozen=True, slots=True)
class ModelInfo:
    model_id: str
    model_revision: str


@dataclass(frozen=True, slots=True)
class StoredAspect:
    aspect_text: str
    aspect_category: str | None
    sentiment_label: SentimentLabel
    sentiment_score: float
    confidence_value: float
    confidence_kind: ConfidenceKind


@dataclass(frozen=True, slots=True)
class StoredResult:
    sentiment_label: SentimentLabel
    sentiment_score: float
    confidence_value: float
    confidence_kind: ConfidenceKind
    aspects: tuple[StoredAspect, ...]
    created_at: datetime
    domain: Domain


@dataclass(frozen=True, slots=True)
class ConfidenceAggregate:
    count: int
    average_value: float | None


@dataclass(frozen=True, slots=True)
class AspectAnalytics:
    aspect_category: str | None
    mention_count: int
    sentiment_counts: dict[SentimentLabel, int]
    average_sentiment_score: float | None


@dataclass(frozen=True, slots=True)
class AnalyticsSummary:
    total_results: int
    sentiment_counts: dict[SentimentLabel, int]
    sentiment_percentages: dict[SentimentLabel, float]
    average_sentiment_score: float | None
    confidence_by_kind: dict[ConfidenceKind, ConfidenceAggregate]
    total_aspect_mentions: int
    aspects_by_category: tuple[AspectAnalytics, ...]
