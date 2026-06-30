from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
from statistics import mean
from typing import Any


def load_pairwise_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            validate_pairwise_record(record, path, line_no)
            records.append(record)
    return records


def validate_pairwise_record(record: dict[str, Any], path: str | Path, line_no: int) -> None:
    for field in ["pair_id", "source_id", "source_split", "prompt", "candidate_a", "candidate_b", "winner", "delta_tag"]:
        if field not in record:
            raise ValueError(f"{path}:{line_no}: missing {field}")
    if record["winner"] not in {"A", "B"}:
        raise ValueError(f"{path}:{line_no}: winner must be A or B")


def read_pairwise_score_rows(path: str | Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            pair_id = row.get("pair_id") or row.get("id")
            if not isinstance(pair_id, str):
                raise ValueError(f"{path}:{line_no}: missing string pair_id")
            rows[pair_id] = row
    return rows


def evaluate_pairwise_scores(
    records: list[dict[str, Any]],
    score_rows: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    total = len(records)
    correct = 0
    missing = 0
    margins: list[float] = []
    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    delta_stats: dict[str, Counter[str]] = defaultdict(Counter)
    gold_action_stats: dict[str, Counter[str]] = defaultdict(Counter)
    source_split_stats: dict[str, Counter[str]] = defaultdict(Counter)
    errors: list[dict[str, Any]] = []

    for record in records:
        pair_id = record["pair_id"]
        expected = record["winner"]
        row = score_rows.get(pair_id)
        if row is None:
            missing += 1
            predicted = "missing"
            margin = None
        else:
            predicted = normalize_winner(row.get("predicted_winner"))
            if predicted is None:
                predicted = winner_from_scores(row.get("scores", {}))
            margin = winner_margin(row.get("scores", {}), expected)

        is_correct = predicted == expected
        if is_correct:
            correct += 1
        else:
            errors.append(error_row(record, predicted, margin))
        if isinstance(margin, (int, float)):
            margins.append(float(margin))

        confusion[expected][predicted or "invalid"] += 1
        add_group_stat(delta_stats[record["delta_tag"]], is_correct)
        add_group_stat(gold_action_stats[record.get("gold_action_mode", record.get("gold_action", ""))], is_correct)
        add_group_stat(source_split_stats[record["source_split"]], is_correct)

    return {
        "total": total,
        "missing_scores": missing,
        "winner_accuracy": correct / total if total else 0.0,
        "average_winner_margin": mean(margins) if margins else None,
        "confusion_matrix": {gold: dict(preds) for gold, preds in sorted(confusion.items())},
        "by_delta_tag": grouped_accuracy(delta_stats),
        "by_gold_action_mode": grouped_accuracy(gold_action_stats),
        "by_source_split": grouped_accuracy(source_split_stats),
        "errors": errors,
    }


def normalize_winner(value: object) -> str | None:
    if isinstance(value, str):
        value = value.strip().upper()
        if value in {"A", "B"}:
            return value
    return None


def winner_from_scores(raw_scores: object) -> str:
    if not isinstance(raw_scores, dict):
        return "invalid"
    score_a = extract_avg_logprob(raw_scores.get("A"))
    score_b = extract_avg_logprob(raw_scores.get("B"))
    if score_a is None and score_b is None:
        return "invalid"
    if score_b is None or (score_a is not None and score_a >= score_b):
        return "A"
    return "B"


def winner_margin(raw_scores: object, expected: str) -> float | None:
    if not isinstance(raw_scores, dict):
        return None
    score_a = extract_avg_logprob(raw_scores.get("A"))
    score_b = extract_avg_logprob(raw_scores.get("B"))
    if score_a is None or score_b is None:
        return None
    return score_a - score_b if expected == "A" else score_b - score_a


def extract_avg_logprob(value: object) -> float | None:
    if isinstance(value, dict):
        value = value.get("avg_logprob", value.get("score"))
    if isinstance(value, (int, float)):
        return float(value)
    return None


def add_group_stat(counter: Counter[str], is_correct: bool) -> None:
    counter["total"] += 1
    if is_correct:
        counter["correct"] += 1


def grouped_accuracy(groups: dict[str, Counter[str]]) -> dict[str, dict[str, float | int]]:
    result: dict[str, dict[str, float | int]] = {}
    for name, counter in sorted(groups.items()):
        total = counter["total"]
        correct = counter["correct"]
        result[name] = {
            "total": total,
            "correct": correct,
            "accuracy": correct / total if total else 0.0,
        }
    return result


def error_row(record: dict[str, Any], predicted: str | None, margin: float | None) -> dict[str, Any]:
    return {
        "pair_id": record["pair_id"],
        "source_id": record["source_id"],
        "source_split": record["source_split"],
        "expected_winner": record["winner"],
        "predicted_winner": predicted or "invalid",
        "winner_margin": margin,
        "gold_action_mode": record.get("gold_action_mode", record.get("gold_action", "")),
        "negative_action": record.get("negative_action", ""),
        "delta_tag": record["delta_tag"],
    }
