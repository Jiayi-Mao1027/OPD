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
    parse_failures = 0
    margins: list[float] = []
    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    delta_stats: dict[str, Counter[str]] = defaultdict(Counter)
    gold_action_stats: dict[str, Counter[str]] = defaultdict(Counter)
    source_split_stats: dict[str, Counter[str]] = defaultdict(Counter)
    source_id_stats: dict[str, Counter[str]] = defaultdict(Counter)
    hard_axis_stats: dict[str, Counter[str]] = defaultdict(Counter)
    scope_error_direction_stats: dict[str, Counter[str]] = defaultdict(Counter)
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
        if predicted == "invalid":
            parse_failures += 1

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
        add_group_stat(source_id_stats[record["source_id"]], is_correct)
        add_group_stat(hard_axis_stats[record_hard_axis(record)], is_correct)
        add_group_stat(scope_error_direction_stats[record_scope_error_direction(record)], is_correct)

    by_hard_axis = grouped_accuracy(hard_axis_stats)
    return {
        "total": total,
        "missing_scores": missing,
        "parse_failures": parse_failures,
        "winner_accuracy": correct / total if total else 0.0,
        "average_winner_margin": mean(margins) if margins else None,
        "confusion_matrix": {gold: dict(preds) for gold, preds in sorted(confusion.items())},
        "by_delta_tag": grouped_accuracy(delta_stats),
        "by_gold_action_mode": grouped_accuracy(gold_action_stats),
        "by_source_split": grouped_accuracy(source_split_stats),
        "by_source_id": grouped_accuracy(source_id_stats),
        "by_hard_axis": by_hard_axis,
        "by_scope_error_direction": grouped_accuracy(scope_error_direction_stats),
        "fork_preservation_accuracy": group_accuracy_value(by_hard_axis.get("fork_state")),
        "scope_contract_accuracy": group_accuracy_value(by_hard_axis.get("scope_contract")),
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


def group_accuracy_value(group: dict[str, float | int] | None) -> float | None:
    if not group:
        return None
    value = group.get("accuracy")
    return float(value) if isinstance(value, (int, float)) else None


def record_hard_axis(record: dict[str, Any]) -> str:
    value = record.get("hard_axis")
    if isinstance(value, str) and value:
        return value
    delta = record.get("delta_tag")
    if delta == "lost_fork_state":
        return "fork_state"
    if delta == "wrong_scope":
        return "scope_contract"
    return "other"


def record_scope_error_direction(record: dict[str, Any]) -> str:
    value = record.get("scope_error_direction")
    if isinstance(value, str) and value:
        return value
    judgment = record.get("gold_judgment")
    if isinstance(judgment, dict):
        value = judgment.get("scope_error_direction")
        if isinstance(value, str) and value:
            return value
    return "none"


def error_row(record: dict[str, Any], predicted: str | None, margin: float | None) -> dict[str, Any]:
    return {
        "pair_id": record["pair_id"],
        "source_id": record["source_id"],
        "source_split": record["source_split"],
        "expected_winner": record["winner"],
        "predicted_winner": predicted or "invalid",
        "winner_margin": margin,
        "gold_action_mode": record.get("gold_action_mode", record.get("gold_action", "")),
        "primary_action": record.get("primary_action", record.get("gold_action_mode", record.get("gold_action", ""))),
        "negative_action": record.get("negative_action", ""),
        "delta_tag": record["delta_tag"],
        "hard_axis": record_hard_axis(record),
        "scope_error_direction": record_scope_error_direction(record),
    }
