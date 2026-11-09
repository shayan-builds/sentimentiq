"""Analytics computed from persisted successful analysis results."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from .types import (
    CONFIDENCE_KINDS, SENTIMENT_LABELS, AnalyticsSummary, AspectAnalytics,
    ConfidenceAggregate, ConfidenceKind, SentimentLabel, StoredResult,
)


def compute_analytics(results: Sequence[StoredResult]) -> AnalyticsSummary:
    """Summarize successful stored results; failed batch rows are not supplied."""
    sentiment_counts: dict[SentimentLabel, int] = {label: 0 for label in SENTIMENT_LABELS}
    confidence_values: dict[ConfidenceKind, list[float]] = {
        kind: [] for kind in CONFIDENCE_KINDS
    }
    aspect_groups: dict[str | None, list[tuple[SentimentLabel, float]]] = defaultdict(list)
    overall_scores: list[float] = []
    total_aspect_mentions = 0

    for result in results:
        sentiment_counts[result.sentiment_label] += 1
        overall_scores.append(result.sentiment_score)
        confidence_values[result.confidence_kind].append(result.confidence_value)
        for aspect in result.aspects:
            total_aspect_mentions += 1
            aspect_groups[aspect.aspect_category].append(
                (aspect.sentiment_label, aspect.sentiment_score)
            )

    total_results = len(results)
    percentages = {
        label: (count * 100.0 / total_results if total_results else 0.0)
        for label, count in sentiment_counts.items()
    }
    confidence_by_kind = {
        kind: ConfidenceAggregate(
            count=len(values),
            average_value=(sum(values) / len(values) if values else None),
        )
        for kind, values in confidence_values.items()
    }
    aspects_by_category = tuple(
        AspectAnalytics(
            aspect_category=category,
            mention_count=len(items),
            sentiment_counts={
                label: sum(1 for item_label, _ in items if item_label == label)
                for label in SENTIMENT_LABELS
            },
            average_sentiment_score=(
                sum(score for _, score in items) / len(items) if items else None
            ),
        )
        for category, items in sorted(
            aspect_groups.items(), key=lambda item: (item[0] is not None, item[0] or "")
        )
    )
    return AnalyticsSummary(
        total_results=total_results,
        sentiment_counts=sentiment_counts,
        sentiment_percentages=percentages,
        average_sentiment_score=(sum(overall_scores) / total_results if total_results else None),
        confidence_by_kind=confidence_by_kind,
        total_aspect_mentions=total_aspect_mentions,
        aspects_by_category=aspects_by_category,
    )
