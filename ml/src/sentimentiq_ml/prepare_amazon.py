"""Prepare Amazon Reviews JSONL files as privacy-minimized weak labels.

This script does not download data. Obtain a permitted research sample yourself,
then run: python -m sentimentiq_ml.prepare_amazon INPUT.jsonl.gz OUTPUT.csv
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
from pathlib import Path
from typing import TextIO


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


def prepare_amazon_jsonl(source: Path, destination: Path, limit: int | None = None) -> dict[str, int]:
    """Export text, star-derived label, and product group only; omit user IDs."""
    counts = {
        "written": 0,
        "missing_text": 0,
        "missing_product_id": 0,
        "unmapped_rating": 0,
        "invalid_json": 0,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    with _open_text(source) as incoming, destination.open(
        "w", newline="", encoding="utf-8"
    ) as outgoing:
        writer = csv.DictWriter(outgoing, fieldnames=("text", "label", "group_id"))
        writer.writeheader()
        for line in incoming:
            if limit is not None and counts["written"] >= limit:
                break
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                counts["invalid_json"] += 1
                continue
            if not isinstance(item, dict):
                counts["invalid_json"] += 1
                continue
            text = item.get("text")
            if not isinstance(text, str) or not text.strip():
                counts["missing_text"] += 1
                continue
            label = rating_label(item.get("rating"))
            if label is None:
                counts["unmapped_rating"] += 1
                continue
            group_id = item.get("parent_asin") or item.get("asin")
            if not isinstance(group_id, str) or not group_id.strip():
                counts["missing_product_id"] += 1
                continue
            writer.writerow({"text": text.strip(), "label": label, "group_id": group_id})
            counts["written"] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Downloaded JSONL or JSONL.GZ review file")
    parser.add_argument("destination", type=Path, help="Output CSV path (keep outside Git)")
    parser.add_argument("--limit", type=int, default=None, help="Maximum valid rows for a small development sample")
    args = parser.parse_args()
    print(prepare_amazon_jsonl(args.source, args.destination, args.limit))


if __name__ == "__main__":
    main()
