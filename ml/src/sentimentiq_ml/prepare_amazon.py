"""Prepare Amazon Reviews JSONL files as privacy-minimized weak labels.

This script does not download data. Obtain a permitted research sample yourself,
then run: python -m sentimentiq_ml.prepare_amazon INPUT.jsonl.gz OUTPUT.csv
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterator, TextIO

_LABELS = ("positive", "negative", "neutral")


def _open_text(path: Path) -> TextIO:
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("rt", encoding="utf-8", errors="replace")


def rating_label(value: object) -> str | None:
    try:
        rating = float(value)
    except (TypeError, ValueError):
        return None
    if 1.0 <= rating <= 2.0:
        return "negative"
    if 2.5 <= rating <= 3.5:
        return "neutral"
    if 4.0 <= rating <= 5.0:
        return "positive"
    return None


def _valid_review(item: object) -> tuple[str, str, str] | str:
    if not isinstance(item, dict):
        return "invalid_json"
    text = item.get("text")
    if not isinstance(text, str) or not text.strip():
        return "missing_text"
    label = rating_label(item.get("rating"))
    if label is None:
        return "unmapped_rating"
    group_id = item.get("parent_asin") or item.get("asin")
    if not isinstance(group_id, str) or not group_id.strip():
        return "missing_product_id"
    return text.strip(), label, group_id.strip()


def _iter_reviews(source: Path) -> Iterator[tuple[str, str, str] | str]:
    with _open_text(source) as incoming:
        for line in incoming:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                yield "invalid_json"
                continue
            yield _valid_review(item)


def _allocate_quotas(group_counts: dict[str, int], target_reviews: int) -> dict[str, int]:
    """Allocate review slots evenly across groups, respecting group availability."""
    quotas = {group_id: 0 for group_id in group_counts}
    remaining = min(target_reviews, sum(group_counts.values()))
    active = list(group_counts)

    while remaining and active:
        share = max(1, remaining // len(active))
        allocated = 0
        for group_id in active:
            capacity = group_counts[group_id] - quotas[group_id]
            addition = min(capacity, share, remaining - allocated)
            if addition > 0:
                quotas[group_id] += addition
                allocated += addition
        remaining -= allocated
        active = [group_id for group_id in active if quotas[group_id] < group_counts[group_id]]

    return quotas


def prepare_amazon_jsonl(
    source: Path,
    destination: Path,
    target_groups: int = 5_000,
    target_reviews: int = 25_000,
    seed: int = 42,
) -> dict[str, object]:
    """Sample product groups, then reviews within groups; omit all user IDs.

    Distinct eligible groups are selected using reservoir sampling. Review quotas
    are spread evenly across the selected groups (up to available reviews), and
    each group's reviews are sampled uniformly without storing the full dataset.
    """
    if target_groups < 1:
        raise ValueError("target_groups must be at least 1")
    if target_reviews < 1:
        raise ValueError("target_reviews must be at least 1")
    group_target = min(target_groups, target_reviews)
    rng = random.Random(seed)
    invalid_counts: Counter[str] = Counter()
    selected_groups: list[str] = []
    seen_groups: set[str] = set()

    # Reservoir-sample distinct groups so the sample is not biased toward early rows.
    for review in _iter_reviews(source):
        if isinstance(review, str):
            invalid_counts[review] += 1
            continue
        _, _, group_id = review
        if group_id in seen_groups:
            continue
        seen_groups.add(group_id)
        group_number = len(seen_groups)
        if len(selected_groups) < group_target:
            selected_groups.append(group_id)
        else:
            replacement = rng.randrange(group_number)
            if replacement < group_target:
                selected_groups[replacement] = group_id

    selected_set = set(selected_groups)
    group_counts: Counter[str] = Counter()
    for review in _iter_reviews(source):
        if not isinstance(review, str) and review[2] in selected_set:
            group_counts[review[2]] += 1

    quotas = _allocate_quotas(dict(group_counts), target_reviews)
    samples: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    seen_review_counts: Counter[str] = Counter()
    for review in _iter_reviews(source):
        if isinstance(review, str) or review[2] not in quotas:
            continue
        group_id = review[2]
        quota = quotas[group_id]
        if quota == 0:
            continue
        seen_review_counts[group_id] += 1
        reservoir = samples[group_id]
        if len(reservoir) < quota:
            reservoir.append(review)
        else:
            replacement = rng.randrange(seen_review_counts[group_id])
            if replacement < quota:
                reservoir[replacement] = review

    label_counts = {label: {"rows": 0, "groups": 0} for label in _LABELS}
    groups_by_label: dict[str, set[str]] = {label: set() for label in _LABELS}
    written = 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as outgoing:
        writer = csv.DictWriter(outgoing, fieldnames=("text", "label", "group_id"))
        writer.writeheader()
        for group_id in selected_groups:
            for text, label, sampled_group_id in samples[group_id]:
                writer.writerow({"text": text, "label": label, "group_id": sampled_group_id})
                written += 1
                label_counts[label]["rows"] += 1
                groups_by_label[label].add(sampled_group_id)
    for label in _LABELS:
        label_counts[label]["groups"] = len(groups_by_label[label])

    return {
        "written": written,
        "distinct_product_groups": len({group_id for group in samples.values() for _, _, group_id in group}),
        "eligible_product_groups": len(seen_groups),
        "target_product_groups": group_target,
        "target_reviews": target_reviews,
        "seed": seed,
        "labels": label_counts,
        **dict(invalid_counts),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Downloaded JSONL or JSONL.GZ review file")
    parser.add_argument("destination", type=Path, help="Output CSV path (keep outside Git)")
    parser.add_argument("--target-groups", type=int, default=5_000, help="Maximum distinct product groups to sample (default: 5000)")
    parser.add_argument("--target-reviews", "--limit", dest="target_reviews", type=int, default=25_000, help="Maximum reviews to sample across selected groups (default: 25000; --limit is an alias)")
    parser.add_argument("--seed", type=int, default=42, help="Fixed random seed for reproducible sampling")
    args = parser.parse_args()
    print(prepare_amazon_jsonl(args.source, args.destination, args.target_groups, args.target_reviews, args.seed))


if __name__ == "__main__":
    main()
