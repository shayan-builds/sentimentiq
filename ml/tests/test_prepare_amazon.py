import csv
import json

from sentimentiq_ml.prepare_amazon import prepare_amazon_jsonl


def _write_reviews(path):
    labels_and_ratings = (("negative", 1), ("neutral", 3), ("positive", 5))
    with path.open("w", encoding="utf-8") as output:
        for group_index in range(30):
            for review_index in range(9):
                label, rating = labels_and_ratings[review_index % len(labels_and_ratings)]
                output.write(json.dumps({
                    "text": f"Review {review_index} for product {group_index}",
                    "rating": rating,
                    "parent_asin": f"product-{group_index}",
                    "reviewer_id": f"private-user-{group_index}-{review_index}",
                }) + "\n")


def test_sampling_is_deterministic_and_spans_product_groups(tmp_path):
    source = tmp_path / "reviews.jsonl"
    first_csv = tmp_path / "first.csv"
    second_csv = tmp_path / "second.csv"
    _write_reviews(source)

    first_report = prepare_amazon_jsonl(source, first_csv, target_groups=8, target_reviews=24, seed=17)
    second_report = prepare_amazon_jsonl(source, second_csv, target_groups=8, target_reviews=24, seed=17)

    assert first_csv.read_bytes() == second_csv.read_bytes()
    with first_csv.open(newline="", encoding="utf-8") as input_file:
        reader = csv.DictReader(input_file)
        rows = list(reader)
        assert reader.fieldnames == ["text", "label", "group_id"]
    selected_groups = {row["group_id"] for row in rows}
    assert len(rows) == 24
    assert len(selected_groups) == 8
    assert any(int(group_id.removeprefix("product-")) >= 8 for group_id in selected_groups)
    assert any(int(row["text"].split()[1]) >= 3 for row in rows)
    assert all("reviewer_id" not in row and "private-user" not in str(row) for row in rows)
    assert first_report == second_report
    assert first_report["written"] == 24
    assert first_report["distinct_product_groups"] == 8


def test_report_counts_rows_and_distinct_groups_per_sentiment(tmp_path):
    source = tmp_path / "reviews.jsonl"
    destination = tmp_path / "reviews.csv"
    _write_reviews(source)

    report = prepare_amazon_jsonl(source, destination, target_groups=6, target_reviews=18, seed=4)

    with destination.open(newline="", encoding="utf-8") as input_file:
        rows = list(csv.DictReader(input_file))
    for label in ("positive", "negative", "neutral"):
        label_rows = [row for row in rows if row["label"] == label]
        assert report["labels"][label] == {
            "rows": len(label_rows),
            "groups": len({row["group_id"] for row in label_rows}),
        }
