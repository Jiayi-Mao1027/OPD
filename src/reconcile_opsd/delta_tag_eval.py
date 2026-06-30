from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def read_delta_tag_score_rows(path: str | Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            pair_id = row.get("pair_id") or row.get("id")
            if not isinstance(pair_id, str):
                raise ValueError(f"{path}:{line_number} missing pair_id")
            rows[pair_id] = row
    return rows


def evaluate_delta_tag_scores(
    records: list[dict[str, Any]], score_rows: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    total = 0
    correct = 0
    missing = 0
    errors: list[dict[str, Any]] = []
    by_expected: dict[str, Counter[str]] = defaultdict(Counter)
    by_hard_axis: dict[str, Counter[str]] = defaultdict(Counter)
    predicted_counts: Counter[str] = Counter()

    for record in records:
        pair_id = record["pair_id"]
        expected = str(record["delta_tag"])
        hard_axis = str(record.get("hard_axis") or "unknown")
        row = score_rows.get(pair_id)
        if row is None:
            missing += 1
            predicted = "missing"
            is_correct = False
            margin = None
        else:
            predicted = str(row.get("predicted_delta_tag", "invalid"))
            is_correct = predicted == expected
            margin = row.get("delta_tag_margin")
        total += 1
        correct += int(is_correct)
        predicted_counts[predicted] += 1
        by_expected[expected]["total"] += 1
        by_expected[expected]["correct"] += int(is_correct)
        by_expected[expected][f"pred:{predicted}"] += 1
        by_hard_axis[hard_axis]["total"] += 1
        by_hard_axis[hard_axis]["correct"] += int(is_correct)
        if not is_correct:
            errors.append(
                {
                    "pair_id": pair_id,
                    "source_id": record.get("source_id"),
                    "expected_delta_tag": expected,
                    "predicted_delta_tag": predicted,
                    "hard_axis": hard_axis,
                    "scope_error_direction": record.get("scope_error_direction"),
                    "winner": record.get("winner"),
                    "delta_tag_margin": margin,
                }
            )

    return {
        "total": total,
        "correct": correct,
        "accuracy": correct / total if total else None,
        "missing_scores": missing,
        "predicted_distribution": dict(predicted_counts),
        "by_expected_delta_tag": summarize_counters(by_expected),
        "by_hard_axis": summarize_counters(by_hard_axis),
        "errors": errors,
    }


def summarize_counters(counters: dict[str, Counter[str]]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for key, counter in counters.items():
        total = counter["total"]
        correct = counter["correct"]
        predictions = {
            pred_key.removeprefix("pred:"): value
            for pred_key, value in counter.items()
            if pred_key.startswith("pred:")
        }
        summary[key] = {
            "total": total,
            "correct": correct,
            "accuracy": correct / total if total else None,
            "predictions": predictions,
        }
    return summary
