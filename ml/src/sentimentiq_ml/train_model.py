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
MIN_HOLDOUT_GROUPS_PER_LABEL = 100


def _load_training_frame(input_csv: Path) -> pd.DataFrame:
    # Preserve legitimate review strings such as "N/A"; blanks are filtered below.
    frame = pd.read_csv(input_csv, keep_default_na=False)
    required_columns = {"text", "label", "group_id"}
    missing_columns = required_columns.difference(frame.columns)
    if missing_columns:
        raise ValueError(f"Training CSV is missing required columns: {', '.join(sorted(missing_columns))}")
    frame = frame[["text", "label", "group_id"]]
    frame = frame.dropna(subset=["text", "label", "group_id"])
    frame["text"] = frame["text"].astype(str).str.strip()
    frame["label"] = frame["label"].astype(str).str.strip().str.lower()
    frame["group_id"] = frame["group_id"].astype(str).str.strip()
    frame = frame[frame["text"].ne("") & frame["label"].isin(_LABELS)]
    frame = frame[frame["group_id"].ne("")]
    if frame.empty:
        raise ValueError("Training CSV has no valid labeled text rows with group IDs")
    if frame["label"].nunique() != 3:
        raise ValueError("Training CSV must contain positive, negative, and neutral labels")
    if frame["group_id"].nunique() < 2:
        raise ValueError("At least two distinct group_id values are required for a holdout split")
    return frame


def _split_by_group(frame: pd.DataFrame, test_size: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not 0.05 <= test_size <= 0.5:
        raise ValueError("test_size must be between 0.05 and 0.5")
    # GroupShuffleSplit preserves product-level separation, but a single random
    # split can omit a class when labels are unevenly distributed by product.
    # Try a bounded, deterministic set of group splits before reporting that
    # the input data cannot support a three-class evaluation.
    split = GroupShuffleSplit(n_splits=32, test_size=test_size, random_state=42)
    best_split: tuple[pd.DataFrame, pd.DataFrame] | None = None
    best_minimum_group_coverage = -1
    for train_idx, test_idx in split.split(frame["text"], frame["label"], groups=frame["group_id"]):
        candidate_train = frame.iloc[train_idx]
        candidate_test = frame.iloc[test_idx]
        if candidate_train["label"].nunique() == 3 and candidate_test["label"].nunique() == 3:
            holdout_groups_by_label = [
                candidate_test.loc[candidate_test["label"] == label, "group_id"].nunique()
                for label in ("positive", "negative", "neutral")
            ]
            minimum_coverage = int(min(holdout_groups_by_label))
            if minimum_coverage > best_minimum_group_coverage:
                best_split = (candidate_train, candidate_test)
                best_minimum_group_coverage = minimum_coverage
            if minimum_coverage >= MIN_HOLDOUT_GROUPS_PER_LABEL:
                break
    if best_split is None:
        raise ValueError(
            "Could not create a group-separated holdout with all three labels in both splits "
            "after 32 deterministic attempts; add more groups per label or adjust --test-size"
        )
    return best_split


def _label_group_counts(frame: pd.DataFrame) -> dict[str, dict[str, int]]:
    """Count rows and distinct product groups represented by each label."""
    return {
        label: {
            "rows": int((frame["label"] == label).sum()),
            "groups": int(frame.loc[frame["label"] == label, "group_id"].nunique()),
        }
        for label in ("positive", "negative", "neutral")
    }


def _holdout_group_check(frame: pd.DataFrame) -> dict[str, object]:
    counts = _label_group_counts(frame)
    per_label = {
        label: {
            "groups": counts[label]["groups"],
            "minimum_required": MIN_HOLDOUT_GROUPS_PER_LABEL,
            "meets_minimum": counts[label]["groups"] >= MIN_HOLDOUT_GROUPS_PER_LABEL,
        }
        for label in ("positive", "negative", "neutral")
    }
    below_minimum = [label for label, coverage in per_label.items() if not coverage["meets_minimum"]]
    return {
        "minimum_groups_per_label": MIN_HOLDOUT_GROUPS_PER_LABEL,
        "passed": not below_minimum,
        "per_label": per_label,
        "labels_below_minimum": below_minimum,
    }


def inspect_training_split(input_csv: Path, test_size: float = 0.2) -> dict[str, object]:
    """Report per-label row and product-group coverage without fitting a model."""
    frame = _load_training_frame(input_csv)
    train_frame, holdout_frame = _split_by_group(frame, test_size)
    holdout_check = _holdout_group_check(holdout_frame)
    return {
        "split": "GroupShuffleSplit(test_size=%.3f, random_state=42, attempts<=32)" % test_size,
        "total_rows": int(len(frame)),
        "total_groups": int(frame["group_id"].nunique()),
        "train": {
            "rows": int(len(train_frame)),
            "groups": int(train_frame["group_id"].nunique()),
            "labels": _label_group_counts(train_frame),
        },
        "holdout": {
            "rows": int(len(holdout_frame)),
            "groups": int(holdout_frame["group_id"].nunique()),
            "labels": _label_group_counts(holdout_frame),
        },
        "holdout_group_check": holdout_check,
    }


def train(input_csv: Path, artifact_path: Path, report_path: Path, test_size: float = 0.2) -> dict[str, object]:
    frame = _load_training_frame(input_csv)
    train_frame, test_frame = _split_by_group(frame, test_size)
    holdout_check = _holdout_group_check(test_frame)
    if not holdout_check["passed"]:
        raise ValueError(
            "Holdout must contain at least 100 distinct product groups per sentiment label; "
            "run --preflight-only to see label-by-label counts"
        )

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
        "split": "GroupShuffleSplit(test_size=%.3f, random_state=42, attempts<=32)" % test_size,
        "train_rows": int(len(train_frame)),
        "holdout_rows": int(len(test_frame)),
        "train_groups": int(train_frame["group_id"].nunique()),
        "holdout_groups": int(test_frame["group_id"].nunique()),
        "group_coverage": {
            "train": _label_group_counts(train_frame),
            "holdout": _label_group_counts(test_frame),
        },
        "holdout_group_check": holdout_check,
        "metrics": report,
        "confidence_note": "predict_proba values are raw, uncalibrated scores",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report_document, indent=2), encoding="utf-8")
    return report_document


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("artifact", type=Path, nargs="?")
    parser.add_argument("report", type=Path, nargs="?")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="report group and label coverage for the deterministic split without training",
    )
    args = parser.parse_args()
    if not 0.05 <= args.test_size <= 0.5:
        parser.error("--test-size must be between 0.05 and 0.5")
    if args.preflight_only:
        split_report = inspect_training_split(args.input_csv, args.test_size)
        print(json.dumps(split_report, indent=2))
        if not split_report["holdout_group_check"]["passed"]:
            raise SystemExit(2)
        return
    if args.artifact is None or args.report is None:
        parser.error("artifact and report paths are required unless --preflight-only is used")
    print(json.dumps(train(args.input_csv, args.artifact, args.report, args.test_size), indent=2))


if __name__ == "__main__":
    main()
