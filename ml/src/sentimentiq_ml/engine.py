"""SentimentIQ v1 lexical baseline.

The default engine uses VADER for polarity and a small domain aspect lexicon.
It is an integration baseline, not a trained or calibrated domain model.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from .types import (
    AnalysisError,
    AnalysisResult,
    AspectResult,
    BatchOutcome,
    Domain,
    ModelInfo,
    Sentiment,
)

logger = logging.getLogger(__name__)

_ASPECT_TERMS: dict[Domain, dict[str, tuple[str, ...]]] = {
    "product": {
        "battery": ("battery life", "battery", "charging"),
        "quality": ("build quality", "quality", "durability", "material"),
        "price": ("value for money", "price", "cost", "value"),
        "performance": ("performance", "speed", "reliability"),
        "design": ("design", "appearance", "color", "colour"),
        "size": ("size", "fit", "comfort"),
        "delivery": ("delivery", "shipping", "packaging"),
        "screen": ("display", "screen", "resolution"),
        "camera": ("camera", "photo quality", "picture quality"),
        "sound": ("sound quality", "sound", "speaker", "audio"),
        "customer_service": ("customer service", "support", "return"),
    },
    "campus": {
        "teaching": ("teaching", "faculty", "professor", "instructor", "lecturer"),
        "curriculum": ("curriculum", "course", "syllabus", "classes"),
        "placements": ("placement", "placements", "internship", "career services"),
        "hostel": ("hostel", "dormitory", "accommodation", "room"),
        "food": ("food", "canteen", "cafeteria", "mess"),
        "facilities": ("facilities", "infrastructure", "laboratory", "lab", "library"),
        "fees": ("fees", "tuition", "scholarship", "financial aid"),
        "transport": ("transport", "bus", "commute", "parking"),
        "campus_environment": ("campus", "cleanliness", "safety", "security"),
        "administration": ("administration", "management", "office", "registrar"),
        "technology": ("wifi", "wi-fi", "internet", "computer", "projector"),
        "exams": ("exam", "exams", "grading", "assessment"),
    },
}
_CONTRAST = re.compile(r"\b(?:but|however|although|though|yet|whereas)\b", re.IGNORECASE)
_SENTENCE = re.compile(r"[^.!?;]+(?:[.!?;]+|$)")
_ASPECT_WORD = r"(?<!\w){}(?!\w)"


@dataclass(frozen=True, slots=True)
class _ScoredText:
    result: Sentiment
    positive: float
    negative: float
    neutral: float


class SentimentEngine:
    """Reusable, process-local VADER baseline engine."""

    def __init__(self) -> None:
        self._analyzer = SentimentIntensityAnalyzer()
        self._vader_model_id = "sentimentiq-vader-baseline"
        self._vader_model_revision = "vaderSentiment-3.3.2"
        self._product_model_id: str | None = None
        self._product_model_revision: str | None = None
        artifact = os.environ.get("SENTIMENTIQ_MODEL_PATH")
        if artifact:
            path = Path(artifact)
            if not path.is_file():
                raise RuntimeError("SENTIMENTIQ_MODEL_PATH does not point to a file")
            # Do not load artifacts from untrusted sources: joblib uses pickle.
            try:
                import joblib
            except ImportError as exc:
                raise RuntimeError("Install the training extra to load a trained artifact") from exc
            bundle: Any = joblib.load(path)
            if not isinstance(bundle, dict) or "pipeline" not in bundle or "model_id" not in bundle:
                raise RuntimeError("The configured model artifact has an unsupported format")
            self._pipeline = bundle["pipeline"]
            self._product_model_id = str(bundle["model_id"])
            self._product_model_revision = sha256(path.read_bytes()).hexdigest()
        else:
            self._pipeline = None

    def get_model_info(self, domain: Domain) -> ModelInfo:
        self._validate_domain(domain)
        if domain == "product" and self._pipeline is not None:
            return ModelInfo(
                model_id=self._product_model_id or "sentimentiq-product-model",
                model_revision=self._product_model_revision or "unknown",
            )
        return ModelInfo(model_id=self._vader_model_id, model_revision=self._vader_model_revision)

    def analyze(self, text: str, domain: Domain) -> AnalysisResult:
        self._validate_domain(domain)
        self._validate_text(text)

        overall_score = self._score(text, domain)
        clause_scores = [self._score(clause, domain) for clause in self._clauses(text)]
        has_positive = any(item.result.sentiment_label == "positive" for item in clause_scores)
        has_negative = any(item.result.sentiment_label == "negative" for item in clause_scores)
        overall = overall_score.result
        if has_positive and has_negative:
            overall = Sentiment(
                sentiment_label="mixed",
                sentiment_score=overall_score.result.sentiment_score,
                confidence_value=min(1.0, 2.0 * min(overall_score.positive, overall_score.negative)),
                confidence_kind="raw_score",
            )

        aspects = self._extract_aspects(text, domain)
        return AnalysisResult(overall=overall, aspects=tuple(aspects))

    def analyze_batch(self, texts: list[str], domain: Domain) -> list[BatchOutcome]:
        self._validate_domain(domain)
        outcomes: list[BatchOutcome] = []
        for index, text in enumerate(texts):
            try:
                outcomes.append(BatchOutcome(input_index=index, result=self.analyze(text, domain)))
            except ValueError:
                outcomes.append(
                    BatchOutcome(
                        input_index=index,
                        error=AnalysisError(code="invalid_text", message="Text must be a nonempty string."),
                    )
                )
            except Exception:
                logger.exception("ML analysis failed for batch input index %s", index)
                outcomes.append(
                    BatchOutcome(
                        input_index=index,
                        error=AnalysisError(
                            code="analysis_failed",
                            message="This row could not be analyzed. Please retry it.",
                        ),
                    )
                )
        return outcomes

    def _extract_aspects(self, text: str, domain: Domain) -> list[AspectResult]:
        terms = sorted(
            ((phrase, category) for category, phrases in _ASPECT_TERMS[domain].items() for phrase in phrases),
            key=lambda item: len(item[0]),
            reverse=True,
        )
        found: list[tuple[int, int, str, str]] = []
        occupied: list[tuple[int, int]] = []
        for phrase, category in terms:
            pattern = re.compile(_ASPECT_WORD.format(re.escape(phrase)), re.IGNORECASE)
            for match in pattern.finditer(text):
                start, end = match.span()
                if any(start < old_end and old_start < end for old_start, old_end in occupied):
                    continue
                occupied.append((start, end))
                found.append((start, end, match.group(0), category))

        results: list[AspectResult] = []
        for start, end, phrase, category in sorted(found):
            context = self._clause_for_offset(text, start)
            # The trained artifact is product-only; campus remains on the
            # explicitly versioned lexical baseline until campus data exists.
            scored = self._score(context, domain)
            results.append(
                AspectResult(
                    aspect_text=phrase,
                    aspect_category=category,
                    sentiment_label=scored.result.sentiment_label,
                    sentiment_score=scored.result.sentiment_score,
                    confidence_value=scored.result.confidence_value,
                    confidence_kind="raw_score",
                    start_offset=start,
                    end_offset=end,
                )
            )
        return results

    def _score(self, text: str, domain: Domain) -> _ScoredText:
        if self._pipeline is not None and domain == "product":
            probabilities = self._pipeline.predict_proba([text])[0]
            labels = self._pipeline.classes_
            scores = {str(label): float(value) for label, value in zip(labels, probabilities)}
            positive = scores.get("positive", 0.0)
            negative = scores.get("negative", 0.0)
            neutral = scores.get("neutral", 0.0)
            score = positive - negative
            label = max(scores, key=scores.get)
            confidence = scores[label]
        else:
            values = self._analyzer.polarity_scores(text)
            score = float(values["compound"])
            positive = float(values["pos"])
            negative = float(values["neg"])
            neutral = float(values["neu"])
            if score >= 0.5:
                label, confidence = "positive", positive
            elif score <= -0.5:
                label, confidence = "negative", negative
            else:
                label, confidence = "neutral", neutral
        return _ScoredText(
            result=Sentiment(
                sentiment_label=label,
                sentiment_score=score,
                confidence_value=confidence,
                confidence_kind="raw_score",
            ),
            positive=positive,
            negative=negative,
            neutral=neutral,
        )

    @staticmethod
    def _trim_span(text: str, start: int, end: int) -> tuple[int, int] | None:
        while start < end and (text[start].isspace() or text[start] in ",:"):
            start += 1
        while end > start and (text[end - 1].isspace() or text[end - 1] in ",:"):
            end -= 1
        return (start, end) if start < end else None

    @classmethod
    def _clause_spans(cls, text: str) -> list[tuple[int, int]]:
        spans: list[tuple[int, int]] = []
        for sentence in _SENTENCE.finditer(text):
            cursor = sentence.start()
            for contrast in _CONTRAST.finditer(text, sentence.start(), sentence.end()):
                trimmed = cls._trim_span(text, cursor, contrast.start())
                if trimmed:
                    spans.append(trimmed)
                cursor = contrast.end()
            trimmed = cls._trim_span(text, cursor, sentence.end())
            if trimmed:
                spans.append(trimmed)
        return spans or [(0, len(text))]

    @classmethod
    def _clauses(cls, text: str) -> list[str]:
        return [text[start:end] for start, end in cls._clause_spans(text)]

    @classmethod
    def _clause_for_offset(cls, text: str, offset: int) -> str:
        for start, end in cls._clause_spans(text):
            if start <= offset < end:
                return text[start:end]
        return text

    @staticmethod
    def _validate_domain(domain: object) -> None:
        if not isinstance(domain, str) or domain not in _ASPECT_TERMS:
            raise ValueError("domain must be 'product' or 'campus'")

    @staticmethod
    def _validate_text(text: object) -> None:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be a nonempty string")


_default_engine: SentimentEngine | None = None


def _engine() -> SentimentEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = SentimentEngine()
    return _default_engine


def get_model_info(domain: Domain) -> ModelInfo:
    return _engine().get_model_info(domain)


def analyze(text: str, domain: Domain) -> AnalysisResult:
    return _engine().analyze(text, domain)


def analyze_batch(texts: list[str], domain: Domain) -> list[BatchOutcome]:
    return _engine().analyze_batch(texts, domain)
