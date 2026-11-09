"""Train a TF-IDF/logistic-regression product baseline from prepared CSV data.

Input CSV columns: text, label, group_id. Split is performed by group_id so
reviews for one product do not appear in both training and holdout sets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline

_LABELS = {"positive", "negative", "neutral"}


def train(input_csv: Path, artifact_path: Path, report_path: Path, test_size: float = 0.2) -> dict[str, object]:
    frame = pd.read_csv(input_csv, usecols=["text", "label", "group_id"])
    frame = frame.dropna(subset=["text", "label", "group_id"])
    frame["text"] = frame["text"].astype(str).str.strip()
    frame["label"] = frame["label"].astype(str).str.strip().str.lower()
    frame["group_id"] = frame["group_id"].astype(str)
    frame = frame[frame["text"].ne("") & frame["label"].isin(_LABELS)]
    if frame["label"].nunique() != 3:
        raise ValueError("Training CSV must contain positive, negative, and neutral labels")
    if frame["group_id"].nunique() < 2:
        raise ValueError("At least two distinct group_id values are required for a holdout split")

    split = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=42)
    train_idx, test_idx = next(split.split(frame["text"], frame["label"], groups=frame["group_id"]))
    train_frame, test_frame = frame.iloc[train_idx], frame.iloc[test_idx]
    if train_frame["label"].nunique() != 3 or test_frame["label"].nunique() != 3:
        raise ValueError("Group holdout must contain all three labels in both splits; add more data/groups")

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=200_000, sublinear_tf=True)),
        ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
    ])
    pipeline.fit(train_frame["text"], train_frame["label"])
    predicted = pipeline.predict(test_frame["text"])
    report = classification_report(
        test_frame["label"], predicted,
        labels=["positive", "negative", "neutral"],
        output_dict=True, zero_division=0,
    )

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact = {
        "pipeline": pipeline,
        "model_id": "sentimentiq-product-tfidf-logreg",
        "training_rows": int(len(train_frame)),
        "training_labels": sorted(train_frame["label"].unique().tolist()),
        "feature_format": "tfidf-word-unigrams-bigrams-v1",
    }
    joblib.dump(artifact, artifact_path)
    revision = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    report_document = {
        "model_id": artifact["model_id"],
        "model_revision": revision,
        "split": "GroupShuffleSplit(test_size=%.3f, random_state=42)" % test_size,
        "train_rows": int(len(train_frame)),
        "holdout_rows": int(len(test_frame)),
        "train_groups": int(train_frame["group_id"].nunique()),
        "holdout_groups": int(test_frame["group_id"].nunique()),
        "metrics": report,
        "confidence_note": "predict_proba values are raw, uncalibrated scores",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report_document, indent=2), encoding="utf-8")
    return report_document


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--test-size", type=float, default=0.2)
    args = parser.parse_args()
    if not 0.05 <= args.test_size <= 0.5:
        parser.error("--test-size must be between 0.05 and 0.5")
    print(json.dumps(train(args.input_csv, args.artifact, args.report, args.test_size), indent=2))


if __name__ == "__main__":
    main()
