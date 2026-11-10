"""Focused, database-free tests for the inference API."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sentimentiq_ml.types import (
    AnalysisError,
    AnalysisResult,
    AspectResult,
    BatchOutcome,
    ModelInfo,
    Sentiment,
)

from backend.app import inference
from backend.app.main import app, lifespan


def _result(label: str, score: float) -> AnalysisResult:
    return AnalysisResult(
        overall=Sentiment(
            sentiment_label=label,  # type: ignore[arg-type]
            sentiment_score=score,
            confidence_value=0.8,
            confidence_kind="raw_score",
        ),
        aspects=(
            AspectResult(
                aspect_text="battery life",
                aspect_category="battery",
                sentiment_label=label,  # type: ignore[arg-type]
                sentiment_score=score,
                confidence_value=0.8,
                confidence_kind="raw_score",
                start_offset=4,
                end_offset=16,
            ),
        ),
    )


def _request(method: str, path: str, payload: dict[str, object] | None = None) -> tuple[int, object]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else b""
    messages: list[dict[str, object]] = []
    request_pending = True

    async def receive() -> dict[str, object]:
        nonlocal request_pending
        if request_pending:
            request_pending = False
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    async def invoke() -> None:
        await app(
            {
                "type": "http",
                "asgi": {"version": "3.0", "spec_version": "2.3"},
                "http_version": "1.1",
                "method": method,
                "scheme": "http",
                "path": path,
                "raw_path": path.encode("ascii"),
                "query_string": b"",
                "root_path": "",
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
                "server": ("testserver", 80),
                "client": ("testclient", 123),
                "state": {},
            },
            receive,
            send,
        )

    asyncio.run(invoke())
    start = next(message for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return int(start["status"]), json.loads(response_body)


class InferenceApiTests(unittest.TestCase):
    def test_valid_product_analysis(self) -> None:
        expected = _result("positive", 0.7)
        with patch.object(inference, "analyze", return_value=expected) as mock_analyze:
            status, body = _request(
                "POST",
                "/api/v1/analyze",
                {"text": "Great battery", "domain": "product"},
            )

        self.assertEqual(status, 200)
        self.assertEqual(body["overall"]["sentiment_label"], "positive")
        self.assertEqual(body["overall"]["confidence_kind"], "raw_score")
        self.assertEqual(body["aspects"][0]["aspect_category"], "battery")
        self.assertEqual(body["aspects"][0]["start_offset"], 4)
        mock_analyze.assert_called_once_with("Great battery", "product")

    def test_valid_campus_analysis(self) -> None:
        with patch.object(inference, "analyze", return_value=_result("negative", -0.6)) as mock_analyze:
            status, body = _request(
                "POST",
                "/api/v1/analyze",
                {"text": "The teaching was poor", "domain": "campus"},
            )

        self.assertEqual(status, 200)
        self.assertEqual(body["overall"]["sentiment_label"], "negative")
        mock_analyze.assert_called_once_with("The teaching was poor", "campus")

    def test_batch_analysis_preserves_order_and_item_status(self) -> None:
        outcomes = [
            BatchOutcome(input_index=0, result=_result("positive", 0.7)),
            BatchOutcome(
                input_index=1,
                error=AnalysisError(code="invalid_text", message="Text must be nonempty."),
            ),
            BatchOutcome(input_index=2, result=_result("negative", -0.7)),
        ]
        texts = ["first", "second", "third"]
        with patch.object(inference, "analyze_batch", return_value=outcomes) as mock_batch:
            status, body = _request(
                "POST",
                "/api/v1/analyze/batch",
                {"texts": texts, "domain": "product"},
            )

        self.assertEqual(status, 200)
        self.assertEqual([item["input_index"] for item in body], [0, 1, 2])
        self.assertEqual([item["status"] for item in body], ["succeeded", "failed", "succeeded"])
        self.assertIsNotNone(body[0]["result"])
        self.assertEqual(body[1]["error"]["code"], "invalid_text")
        self.assertEqual(body[2]["result"]["overall"]["sentiment_label"], "negative")
        mock_batch.assert_called_once_with(texts, "product")

    def test_invalid_domain_is_rejected(self) -> None:
        status, body = _request(
            "POST",
            "/api/v1/analyze",
            {"text": "Review", "domain": "other"},
        )
        self.assertEqual(status, 422)
        self.assertEqual(body["detail"][0]["loc"][-1], "domain")

    def test_empty_text_is_rejected(self) -> None:
        status, body = _request(
            "POST",
            "/api/v1/analyze",
            {"text": "   ", "domain": "product"},
        )
        self.assertEqual(status, 422)
        self.assertEqual(body["detail"][0]["loc"][-1], "text")

    def test_empty_batch_is_rejected(self) -> None:
        status, body = _request(
            "POST",
            "/api/v1/analyze/batch",
            {"texts": [], "domain": "product"},
        )
        self.assertEqual(status, 422)
        self.assertEqual(body["detail"][0]["loc"][-1], "texts")

    def test_lifespan_initializes_product_model_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            artifact = Path(temporary_directory) / "model.joblib"
            artifact.write_bytes(b"test placeholder; model loading is mocked")

            async def enter_lifespan() -> None:
                with patch.dict(os.environ, {"SENTIMENTIQ_MODEL_PATH": str(artifact)}):
                    with patch(
                        "backend.app.main.get_model_info",
                        return_value=ModelInfo("product-model", "test-revision"),
                    ) as mock_get_model_info:
                        async with lifespan(app):
                            self.assertEqual(
                                app.state.product_model_info.model_revision,
                                "test-revision",
                            )
                        mock_get_model_info.assert_called_once_with("product")

            asyncio.run(enter_lifespan())

    def test_lifespan_fails_clearly_without_model_path(self) -> None:
        async def enter_lifespan() -> None:
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(RuntimeError, "SENTIMENTIQ_MODEL_PATH"):
                    async with lifespan(app):
                        self.fail("lifespan should not start without model configuration")

        asyncio.run(enter_lifespan())


if __name__ == "__main__":
    unittest.main()
