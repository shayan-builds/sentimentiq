import csv

import pytest


def test_preflight_reports_distinct_product_groups_per_label(tmp_path):
    pytest.importorskip("pandas")
    pytest.importorskip("sklearn")
    pytest.importorskip("joblib")
    from sentimentiq_ml.train_model import inspect_training_split

    dataset = tmp_path / "reviews.csv"
    with dataset.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=("text", "label", "group_id"))
        writer.writeheader()
        for group_index in range(30):
            for label in ("positive", "negative", "neutral"):
                writer.writerow({
                    "text": f"{label} review for product {group_index}",
                    "label": label,
                    "group_id": f"product-{group_index}",
                })

    report = inspect_training_split(dataset, test_size=0.2)

    assert report["total_rows"] == 90
    assert report["total_groups"] == 30
    assert report["holdout"]["groups"] == 6
    assert report["train"]["groups"] == 24
    assert report["holdout_group_check"]["minimum_groups_per_label"] == 100
    assert report["holdout_group_check"]["passed"] is False
    assert report["holdout_group_check"]["labels_below_minimum"] == ["positive", "negative", "neutral"]
    for split_name, expected_groups in (("train", 24), ("holdout", 6)):
        for label in ("positive", "negative", "neutral"):
            coverage = report[split_name]["labels"][label]
            assert coverage["rows"] == expected_groups
            assert coverage["groups"] == expected_groups


def test_preflight_passes_when_each_holdout_label_has_100_groups(tmp_path):
    pytest.importorskip("pandas")
    pytest.importorskip("sklearn")
    pytest.importorskip("joblib")
    from sentimentiq_ml.train_model import inspect_training_split

    dataset = tmp_path / "reviews.csv"
    with dataset.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=("text", "label", "group_id"))
        writer.writeheader()
        for group_index in range(600):
            for label in ("positive", "negative", "neutral"):
                writer.writerow({
                    "text": f"{label} review for product {group_index}",
                    "label": label,
                    "group_id": f"product-{group_index}",
                })

    report = inspect_training_split(dataset, test_size=0.2)

    assert report["holdout_group_check"]["passed"] is True
    assert report["holdout_group_check"]["labels_below_minimum"] == []
    for label in ("positive", "negative", "neutral"):
        assert report["holdout_group_check"]["per_label"][label]["groups"] == 120
