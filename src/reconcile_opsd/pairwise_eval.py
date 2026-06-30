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
    gold_winner_counts: Counter[str] = Counter()
    predicted_winner_counts: Counter[str] = Counter()
    expected_side_stats: dict[str, Counter[str]] = defaultdict(Counter)
    expected_side_margins: dict[str, list[float]] = defaultdict(list)
    score_diffs: list[float] = []
    chosen_action_counts: Counter[str] = Counter()
    score_mode_counts: Counter[str] = Counter()
    errors: list[dict[str, Any]] = []

    for record in records:
        pair_id = record["pair_id"]
        expected = record["winner"]
        row = score_rows.get(pair_id)
        predicted = predicted_from_score_row(row)
        if predicted == "missing":
            missing += 1
            margin = None
        else:
            margin = winner_margin(row.get("scores", {}) if row else {}, expected)
        if predicted == "invalid":
            parse_failures += 1
        score_diff = score_a_minus_b(row.get("scores", {}) if row else {})
        if score_diff is not None:
            score_diffs.append(score_diff)
        score_mode = row.get("score_mode") if row else None
        if isinstance(score_mode, str) and score_mode:
            score_mode_counts[score_mode] += 1

        is_correct = predicted == expected
        if is_correct:
            correct += 1
        else:
            errors.append(error_row(record, predicted, margin))
        if isinstance(margin, (int, float)):
            margins.append(float(margin))

        confusion[expected][predicted or "invalid"] += 1
        gold_winner_counts[expected] += 1
        predicted_winner_counts[predicted or "invalid"] += 1
        add_group_stat(expected_side_stats[expected], is_correct)
        if isinstance(margin, (int, float)):
            expected_side_margins[expected].append(float(margin))
        if predicted in {"A", "B"}:
            chosen_action_counts[chosen_action(record, predicted)] += 1
        add_group_stat(delta_stats[record["delta_tag"]], is_correct)
        add_group_stat(gold_action_stats[record.get("gold_action_mode", record.get("gold_action", ""))], is_correct)
        add_group_stat(source_split_stats[record["source_split"]], is_correct)
        add_group_stat(source_id_stats[record["source_id"]], is_correct)
        add_group_stat(hard_axis_stats[record_hard_axis(record)], is_correct)
        add_group_stat(scope_error_direction_stats[record_scope_error_direction(record)], is_correct)

    by_hard_axis = grouped_accuracy(hard_axis_stats)
    pred_a_rate = predicted_winner_counts["A"] / total if total else 0.0
    pred_b_rate = predicted_winner_counts["B"] / total if total else 0.0
    swap_diagnostics = compute_swap_diagnostics(records, score_rows)
    swap_consistency = swap_diagnostics["consistency"]
    by_expected_side = grouped_accuracy_with_margins(expected_side_stats, expected_side_margins)
    side_bias = side_bias_metrics(
        total=total,
        gold_counts=gold_winner_counts,
        predicted_counts=predicted_winner_counts,
        by_expected_side=by_expected_side,
    )
    score_bias = score_side_bias_metrics(score_diffs)
    position_bias_flag = (
        pred_a_rate > 0.75
        or pred_b_rate > 0.75
        or side_bias["predicted_majority_rate"] > 0.80
        or abs(side_bias["predicted_a_rate_minus_gold_a_rate"]) > 0.20
        or (side_bias["min_expected_side_accuracy"] is not None and side_bias["min_expected_side_accuracy"] < 0.50)
        or (swap_consistency is not None and swap_consistency < 0.70)
    )
    return {
        "total": total,
        "missing_scores": missing,
        "parse_failures": parse_failures,
        "winner_accuracy": correct / total if total else 0.0,
        "average_winner_margin": mean(margins) if margins else None,
        "confusion_matrix": {gold: dict(preds) for gold, preds in sorted(confusion.items())},
        "gold_winner_counts": dict(sorted(gold_winner_counts.items())),
        "predicted_winner_counts": dict(sorted(predicted_winner_counts.items())),
        "gold_A_rate": gold_winner_counts["A"] / total if total else 0.0,
        "gold_B_rate": gold_winner_counts["B"] / total if total else 0.0,
        "pred_A_rate": pred_a_rate,
        "pred_B_rate": pred_b_rate,
        "A_recall": confusion["A"]["A"] / gold_winner_counts["A"] if gold_winner_counts["A"] else None,
        "B_recall": confusion["B"]["B"] / gold_winner_counts["B"] if gold_winner_counts["B"] else None,
        "by_expected_side": by_expected_side,
        "side_bias": side_bias,
        "score_side_bias": score_bias,
        "chosen_action_distribution": dict(sorted(chosen_action_counts.items())),
        "score_mode_counts": dict(sorted(score_mode_counts.items())),
        "swap_consistency": swap_consistency,
        "swap_diagnostics": swap_diagnostics,
        "position_bias_flag": position_bias_flag,
        "position_bias_gate": {
            "pred_rate_threshold": 0.75,
            "predicted_majority_rate_threshold": 0.80,
            "predicted_a_rate_delta_threshold": 0.20,
            "min_expected_side_accuracy_threshold": 0.50,
            "swap_consistency_threshold": 0.70,
            "status": "fail" if position_bias_flag else "pass",
        },
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


def predicted_from_score_row(row: dict[str, Any] | None) -> str:
    if row is None:
        return "missing"
    predicted = normalize_winner(row.get("predicted_winner"))
    if predicted is None:
        predicted = winner_from_scores(row.get("scores", {}))
    return predicted or "invalid"


def compute_swap_consistency(records: list[dict[str, Any]], score_rows: dict[str, dict[str, Any]]) -> float | None:
    return compute_swap_diagnostics(records, score_rows)["consistency"]


def compute_swap_diagnostics(records: list[dict[str, Any]], score_rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for record in records:
        parent_pair_id = record.get("parent_pair_id")
        variant = record.get("position_variant")
        if not isinstance(parent_pair_id, str) or not isinstance(variant, str):
            continue
        if variant not in {"original", "swapped"}:
            continue
        grouped[parent_pair_id][variant] = record

    comparable = 0
    consistent = 0
    rows: list[dict[str, Any]] = []
    for parent_pair_id, variants in sorted(grouped.items()):
        original = variants.get("original")
        swapped = variants.get("swapped")
        if not original or not swapped:
            continue
        original_row = score_rows.get(original["pair_id"])
        swapped_row = score_rows.get(swapped["pair_id"])
        original_pred = predicted_from_score_row(original_row)
        swapped_pred = predicted_from_score_row(swapped_row)
        if original_pred not in {"A", "B"} or swapped_pred not in {"A", "B"}:
            continue
        original_margin = winner_margin(original_row.get("scores", {}) if original_row else {}, original["winner"])
        swapped_margin = winner_margin(swapped_row.get("scores", {}) if swapped_row else {}, swapped["winner"])
        original_correct = original_pred == original["winner"]
        swapped_correct = swapped_pred == swapped["winner"]
        is_consistent = original_pred != swapped_pred
        comparable += 1
        if is_consistent:
            consistent += 1
        rows.append(
            {
                "parent_pair_id": parent_pair_id,
                "source_id": original["source_id"],
                "hard_axis": record_hard_axis(original),
                "delta_tag": original["delta_tag"],
                "scope_error_direction": record_scope_error_direction(original),
                "original_pair_id": original["pair_id"],
                "swapped_pair_id": swapped["pair_id"],
                "original_expected": original["winner"],
                "original_predicted": original_pred,
                "original_correct": original_correct,
                "original_margin": original_margin,
                "original_chosen_action": chosen_action(original, original_pred),
                "swapped_expected": swapped["winner"],
                "swapped_predicted": swapped_pred,
                "swapped_correct": swapped_correct,
                "swapped_margin": swapped_margin,
                "swapped_chosen_action": chosen_action(swapped, swapped_pred),
                "consistent": is_consistent,
                "both_correct": original_correct and swapped_correct,
                "both_wrong": (not original_correct) and (not swapped_correct),
                "near_tie": is_near_tie(original_margin) or is_near_tie(swapped_margin),
                "min_abs_margin": min_abs_margin(original_margin, swapped_margin),
            }
        )
    inconsistent_rows = [row for row in rows if not row["consistent"]]
    return {
        "comparable": comparable,
        "consistent": consistent,
        "inconsistent": len(inconsistent_rows),
        "consistency": consistent / comparable if comparable else None,
        "rows": rows,
        "inconsistent_rows": inconsistent_rows,
    }


def side_bias_metrics(
    *,
    total: int,
    gold_counts: Counter[str],
    predicted_counts: Counter[str],
    by_expected_side: dict[str, dict[str, float | int | None]],
) -> dict[str, Any]:
    valid_predicted = predicted_counts["A"] + predicted_counts["B"]
    pred_a_rate = predicted_counts["A"] / total if total else 0.0
    pred_b_rate = predicted_counts["B"] / total if total else 0.0
    gold_a_rate = gold_counts["A"] / total if total else 0.0
    majority_side = "A" if predicted_counts["A"] >= predicted_counts["B"] else "B"
    majority_rate = max(predicted_counts["A"], predicted_counts["B"]) / valid_predicted if valid_predicted else 0.0
    side_gap = abs(predicted_counts["A"] - predicted_counts["B"]) / valid_predicted if valid_predicted else None
    side_accs = [
        float(stats["accuracy"])
        for side in ["A", "B"]
        if (stats := by_expected_side.get(side)) and isinstance(stats.get("accuracy"), (int, float))
    ]
    return {
        "predicted_majority_side": majority_side,
        "predicted_majority_rate": majority_rate,
        "side_gap": side_gap,
        "predicted_a_rate_minus_gold_a_rate": pred_a_rate - gold_a_rate,
        "side_entropy_bits": binary_entropy(pred_a_rate, pred_b_rate),
        "min_expected_side_accuracy": min(side_accs) if side_accs else None,
    }


def score_side_bias_metrics(score_diffs: list[float]) -> dict[str, float | int | None]:
    if not score_diffs:
        return {
            "count": 0,
            "mean_score_a_minus_b": None,
            "median_score_a_minus_b": None,
            "near_tie_rate_abs_le_0_01": None,
        }
    ordered = sorted(score_diffs)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        median = ordered[midpoint]
    else:
        median = (ordered[midpoint - 1] + ordered[midpoint]) / 2
    return {
        "count": len(score_diffs),
        "mean_score_a_minus_b": mean(score_diffs),
        "median_score_a_minus_b": median,
        "near_tie_rate_abs_le_0_01": sum(1 for value in score_diffs if abs(value) <= 0.01) / len(score_diffs),
    }


def binary_entropy(rate_a: float, rate_b: float) -> float:
    import math

    entropy = 0.0
    for rate in [rate_a, rate_b]:
        if rate > 0:
            entropy -= rate * math.log2(rate)
    return entropy


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


def score_a_minus_b(raw_scores: object) -> float | None:
    if not isinstance(raw_scores, dict):
        return None
    score_a = extract_avg_logprob(raw_scores.get("A"))
    score_b = extract_avg_logprob(raw_scores.get("B"))
    if score_a is None or score_b is None:
        return None
    return score_a - score_b


def is_near_tie(margin: float | None, threshold: float = 0.01) -> bool:
    return isinstance(margin, (int, float)) and abs(float(margin)) <= threshold


def min_abs_margin(left: float | None, right: float | None) -> float | None:
    values = [abs(float(value)) for value in [left, right] if isinstance(value, (int, float))]
    return min(values) if values else None


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


def grouped_accuracy_with_margins(
    groups: dict[str, Counter[str]],
    margins: dict[str, list[float]],
) -> dict[str, dict[str, float | int | None]]:
    result: dict[str, dict[str, float | int | None]] = {}
    for name, counter in sorted(groups.items()):
        total = counter["total"]
        correct = counter["correct"]
        group_margins = margins.get(name, [])
        result[name] = {
            "total": total,
            "correct": correct,
            "accuracy": correct / total if total else 0.0,
            "average_winner_margin": mean(group_margins) if group_margins else None,
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


def chosen_action(record: dict[str, Any], predicted: str) -> str:
    candidate_key = "candidate_a" if predicted == "A" else "candidate_b"
    candidate = record.get(candidate_key)
    if isinstance(candidate, dict):
        value = candidate.get("action_mode")
        if isinstance(value, str) and value:
            return value
        decision_card = candidate.get("decision_card")
        if isinstance(decision_card, dict):
            value = decision_card.get("primary_action")
            if isinstance(value, str) and value:
                return value
    return "unknown"


def error_row(record: dict[str, Any], predicted: str | None, margin: float | None) -> dict[str, Any]:
    predicted_value = predicted or "invalid"
    return {
        "pair_id": record["pair_id"],
        "source_id": record["source_id"],
        "source_split": record["source_split"],
        "expected_winner": record["winner"],
        "predicted_winner": predicted_value,
        "winner_margin": margin,
        "candidate_a_action": chosen_action(record, "A"),
        "candidate_b_action": chosen_action(record, "B"),
        "chosen_action": chosen_action(record, predicted_value) if predicted_value in {"A", "B"} else "invalid",
        "gold_action_mode": record.get("gold_action_mode", record.get("gold_action", "")),
        "primary_action": record.get("primary_action", record.get("gold_action_mode", record.get("gold_action", ""))),
        "negative_action": record.get("negative_action", ""),
        "delta_tag": record["delta_tag"],
        "hard_axis": record_hard_axis(record),
        "scope_error_direction": record_scope_error_direction(record),
    }
