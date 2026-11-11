
import csv
import json

from sentimentiq_ml.prepare_amazon import (
    prepare_amazon_jsonl,
    rating_label,
)


def test_rating_label_mapping():
    assert rating_label(1) == "negative"
    assert rating_label(2) == "negative"
    assert rating_label(3) == "neutral"
    assert rating_label(4) == "positive"
    assert rating_label(5) == "positive"
    assert rating_label(2.4) is None
    assert rating_label("invalid") is None


def test_prepare_amazon_extracts_required_fields(tmp_path):
    source = tmp_path / "reviews.jsonl"
    destination = tmp_path / "reviews.csv"

    records = [
        {
            "text": "Excellent product",
            "rating": 5,
            "parent_asin": "GROUP001",
            "asin": "ITEM001",
            "user_id": "PRIVATE_USER",
        },
        {
            "text": "Terrible product",
            "rating": 1,
            "asin": "ITEM002",
            "user_id": "PRIVATE_USER",
        },
    ]

    source.write_text(
        "\n".join(json.dumps(record) for record in records),
        encoding="utf-8",
    )

    counts = prepare_amazon_jsonl(source, destination)

    with destination.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert counts["written"] == 2
    assert rows[0] == {
        "text": "Excellent product",
        "label": "positive",
        "group_id": "GROUP001",
    }
    assert rows[1] == {
        "text": "Terrible product",
        "label": "negative",
        "group_id": "ITEM002",
    }

    assert "user_id" not in rows[0]
    assert "user_id" not in rows[1]
