"""Pydantic contracts for the inference API."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


Domain = Literal["product", "campus"]
SentimentLabel = Literal["positive", "negative", "neutral", "mixed"]
ConfidenceKind = Literal["raw_score", "calibrated_probability"]
InputText = Annotated[str, Field(min_length=1, max_length=10_000)]


class AnalysisRequest(BaseModel):
    text: InputText
    domain: Domain

    @field_validator("text")
    @classmethod
    def text_must_not_be_whitespace(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must contain non-whitespace characters")
        return value


class BatchAnalysisRequest(BaseModel):
    texts: Annotated[list[InputText], Field(min_length=1, max_length=100)]
    domain: Domain

    @field_validator("texts")
    @classmethod
    def texts_must_not_be_whitespace(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("each text must contain non-whitespace characters")
        return values


class SentimentResponse(BaseModel):
    sentiment_label: SentimentLabel
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    confidence_value: float = Field(ge=0.0, le=1.0)
    confidence_kind: ConfidenceKind


class AspectResponse(SentimentResponse):
    aspect_text: str
    aspect_category: str | None = None
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=1)


class AnalysisResponse(BaseModel):
    overall: SentimentResponse
    aspects: list[AspectResponse]


class AnalysisErrorResponse(BaseModel):
    code: str
    message: str


class BatchOutcomeResponse(BaseModel):
    input_index: int = Field(ge=0)
    status: Literal["succeeded", "failed"]
    result: AnalysisResponse | None = None
    error: AnalysisErrorResponse | None = None

    @model_validator(mode="after")
    def outcome_matches_status(self) -> BatchOutcomeResponse:
        if self.status == "succeeded" and (self.result is None or self.error is not None):
            raise ValueError("a succeeded outcome must contain only a result")
        if self.status == "failed" and (self.error is None or self.result is not None):
            raise ValueError("a failed outcome must contain only an error")
        return self
