from datetime import datetime, timezone

import pytest

from sentimentiq_ml import (
    AnalysisError,
    AnalysisResult,
    AspectResult,
    BatchOutcome,
    Sentiment,
    StoredAspect,
    StoredResult,
    analyze,
    analyze_batch,
    compute_analytics,
    get_model_info,
)


def test_sentiment_and_offsets_validate_contract_ranges():
    with pytest.raises(ValueError):
        Sentiment("positive", 1.1, 0.5, "raw_score")
    with pytest.raises(ValueError):
        AspectResult("battery", "positive", 0.4, 0.8, "raw_score", start_offset=2)


def test_batch_preserves_order_and_returns_one_result_or_error_per_input():
    outcomes = analyze_batch(["Great battery!", "  "], "product")

    assert [item.input_index for item in outcomes] == [0, 1]
    assert isinstance(outcomes[0].result, AnalysisResult)
    assert outcomes[0].error is None
    assert outcomes[1].result is None
    assert outcomes[1].error == AnalysisError("invalid_text", "Text must be a nonempty string.")


def test_aspect_mentions_are_repeated_and_offsets_address_original_unicode_text():
    text = "😊 Great battery, but the battery is absolutely terrible and useless."
    result = analyze(text, "product")
    mentions = [item for item in result.aspects if item.aspect_category == "battery"]

    assert len(mentions) == 2
    assert [text[item.start_offset:item.end_offset] for item in mentions] == ["battery", "battery"]
    assert [item.sentiment_label for item in mentions] == ["positive", "negative"]


def test_model_info_is_domain_aware():
    assert get_model_info("product").model_id == "sentimentiq-vader-baseline"
    assert get_model_info("campus").model_revision == "vaderSentiment-3.3.2"


def test_analytics_use_successful_rows_and_group_confidence_by_kind():
    results = [
        StoredResult(
            sentiment_label="positive",
            sentiment_score=0.75,
            confidence_value=0.8,
            confidence_kind="raw_score",
            aspects=(StoredAspect("battery", "battery", "positive", 0.75, 0.8, "raw_score"),),
            created_at=datetime.now(timezone.utc),
            domain="product",
        ),
        StoredResult(
            sentiment_label="negative",
            sentiment_score=-0.5,
            confidence_value=0.9,
            confidence_kind="calibrated_probability",
            aspects=(),
            created_at=datetime.now(timezone.utc),
            domain="product",
        ),
    ]

    summary = compute_analytics(results)
    assert summary.total_results == 2
    assert summary.sentiment_percentages["positive"] == 50.0
    assert summary.confidence_by_kind["raw_score"].count == 1
    assert summary.confidence_by_kind["calibrated_probability"].average_value == 0.9
    assert summary.total_aspect_mentions == 1
