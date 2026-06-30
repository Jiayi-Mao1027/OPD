from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from reconcile_opsd.compact_generation import COMPACT_FIELD_ORDER, normalize_field_value


@dataclass(frozen=True)
class GenerationRun:
    name: str
    path: Path


def parse_run_spec(spec: str) -> GenerationRun:
    if "=" not in spec:
        raise ValueError(f"generation spec must be name=path, got: {spec}")
    name, path = spec.split("=", 1)
    if not name.strip() or not path.strip():
        raise ValueError(f"generation spec must be name=path, got: {spec}")
    return GenerationRun(name=name.strip(), path=Path(path.strip()))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def summarize_generation_run(name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    expected_value_to_fields = build_expected_value_index(rows)
    field_name_values = {normalize_field_value(field): field for field in COMPACT_FIELD_ORDER}

    field_stats: dict[str, dict[str, Any]] = {}
    by_hard_axis: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "winner_correct": 0, "field_correct": 0, "field_total": 0, "full_matches": 0}
    )
    missing_counter: Counter[str] = Counter()
    wrong_counter: Counter[str] = Counter()
    confusion_counter: Counter[tuple[str, str, str]] = Counter()
    present_counts: list[int] = []
    all_expected_present = 0
    full_matches = 0
    winner_correct = 0
    parse_failures = 0
    sample_rows: list[dict[str, Any]] = []

    for field in COMPACT_FIELD_ORDER:
        field_stats[field] = {
            "expected": 0,
            "present": 0,
            "correct": 0,
            "parsed_values": Counter(),
            "mismatches": Counter(),
        }

    for row in rows:
        expected = coerce_str_dict(row.get("expected_fields"))
        parsed = coerce_str_dict(row.get("parsed_fields"))
        present_counts.append(len(parsed))
        expected_total = len(expected)
        correct_fields = 0
        missing_fields: list[str] = []
        wrong_fields: dict[str, dict[str, str | None]] = {}
        row_confusions: list[str] = []

        if row.get("parse_status") == "failed" or row.get("parse_failure"):
            parse_failures += 1
        if row.get("predicted_winner") == row.get("expected_winner"):
            winner_correct += 1

        for field, expected_value in expected.items():
            if field not in field_stats:
                field_stats[field] = {
                    "expected": 0,
                    "present": 0,
                    "correct": 0,
                    "parsed_values": Counter(),
                    "mismatches": Counter(),
                }
            stats = field_stats[field]
            stats["expected"] += 1
            parsed_value = parsed.get(field)
            if parsed_value is None:
                missing_counter[field] += 1
                missing_fields.append(field)
                wrong_fields[field] = {"expected": expected_value, "parsed": None}
                continue
            stats["present"] += 1
            stats["parsed_values"][parsed_value] += 1
            if normalize_field_value(parsed_value) == normalize_field_value(expected_value):
                stats["correct"] += 1
                correct_fields += 1
            else:
                wrong_counter[field] += 1
                stats["mismatches"][(expected_value, parsed_value)] += 1
                wrong_fields[field] = {"expected": expected_value, "parsed": parsed_value}
                for label in classify_confusion(
                    field=field,
                    expected_value=expected_value,
                    parsed_value=parsed_value,
                    expected_value_to_fields=expected_value_to_fields,
                    field_name_values=field_name_values,
                ):
                    confusion_counter[(field, parsed_value, label)] += 1
                    row_confusions.append(f"{field}={parsed_value} ({label})")

        if expected_total and correct_fields == expected_total:
            full_matches += 1
        row_full_match = bool(expected_total and correct_fields == expected_total)
        if expected and all(field in parsed for field in expected):
            all_expected_present += 1

        axis = expected.get("HARD_AXIS", "unknown")
        axis_stats = by_hard_axis[axis]
        axis_stats["total"] += 1
        axis_stats["winner_correct"] += int(row.get("predicted_winner") == row.get("expected_winner"))
        axis_stats["field_correct"] += correct_fields
        axis_stats["field_total"] += expected_total
        axis_stats["full_matches"] += int(row_full_match)

        if expected_total == 0:
            field_accuracy = None
        else:
            field_accuracy = correct_fields / expected_total
        sample_rows.append(
            {
                "run": name,
                "pair_id": row.get("pair_id") or row.get("id"),
                "source_id": row.get("source_id"),
                "hard_axis": expected.get("HARD_AXIS"),
                "delta_tag": expected.get("DELTA_TAG"),
                "scope_error_direction": expected.get("SCOPE_ERROR_DIRECTION"),
                "is_swapped": str(row.get("pair_id") or row.get("id") or "").endswith("__swapped"),
                "parse_status": row.get("parse_status"),
                "expected_winner": row.get("expected_winner"),
                "predicted_winner": row.get("predicted_winner"),
                "winner_correct": row.get("predicted_winner") == row.get("expected_winner"),
                "field_correct": correct_fields,
                "field_total": expected_total,
                "field_accuracy": field_accuracy,
                "missing_fields": ",".join(missing_fields),
                "wrong_fields": compact_wrong_fields(wrong_fields),
                "schema_confusions": "; ".join(row_confusions),
                "raw_generation": normalize_raw_generation(row.get("raw_generation") or row.get("generated_text") or ""),
            }
        )

    total = len(rows)
    return {
        "name": name,
        "total": total,
        "winner_correct": winner_correct,
        "winner_accuracy": safe_div(winner_correct, total),
        "parse_failures": parse_failures,
        "parse_failure_rate": safe_div(parse_failures, total),
        "avg_present_fields": safe_div(sum(present_counts), total),
        "all_expected_present": all_expected_present,
        "all_expected_present_rate": safe_div(all_expected_present, total),
        "full_matches": full_matches,
        "full_match_rate": safe_div(full_matches, total),
        "missing_fields": missing_counter,
        "wrong_fields": wrong_counter,
        "field_stats": finalize_field_stats(field_stats),
        "confusions": confusion_counter,
        "by_hard_axis": finalize_axis_stats(by_hard_axis),
        "samples": rank_samples(sample_rows),
    }


def build_expected_value_index(rows: Iterable[dict[str, Any]]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        for field, value in coerce_str_dict(row.get("expected_fields")).items():
            norm = normalize_field_value(value)
            if norm:
                index[norm].add(field)
    return index


def coerce_str_dict(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(val) for key, val in value.items() if val is not None}


def classify_confusion(
    *,
    field: str,
    expected_value: str,
    parsed_value: str,
    expected_value_to_fields: dict[str, set[str]],
    field_name_values: dict[str, str],
) -> list[str]:
    labels: list[str] = []
    parsed_norm = normalize_field_value(parsed_value)
    expected_norm = normalize_field_value(expected_value)
    if not parsed_norm:
        return labels

    field_name = field_name_values.get(parsed_norm)
    if field_name is not None:
        labels.append(f"value_is_field_name:{field_name}")

    for other_field in sorted(expected_value_to_fields.get(parsed_norm, set())):
        if other_field != field:
            labels.append(f"value_from_expected_{other_field}")

    if parsed_norm and expected_norm and parsed_norm != expected_norm:
        if expected_norm.startswith(parsed_norm) or parsed_norm.startswith(expected_norm):
            labels.append("possible_truncation_or_alias")
    return labels


def compact_wrong_fields(wrong_fields: dict[str, dict[str, str | None]]) -> str:
    parts: list[str] = []
    for field in COMPACT_FIELD_ORDER:
        if field not in wrong_fields:
            continue
        values = wrong_fields[field]
        parts.append(f"{field}: {values['expected']} -> {values['parsed']}")
    return "; ".join(parts)


def normalize_raw_generation(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " | ".join(part.strip() for part in value.strip().splitlines() if part.strip())


def finalize_field_stats(field_stats: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    finalized: dict[str, dict[str, Any]] = {}
    for field in COMPACT_FIELD_ORDER:
        stats = field_stats.get(field)
        if not stats:
            continue
        expected = int(stats["expected"])
        present = int(stats["present"])
        correct = int(stats["correct"])
        finalized[field] = {
            "expected": expected,
            "present": present,
            "missing": expected - present,
            "correct": correct,
            "present_rate": safe_div(present, expected),
            "accuracy": safe_div(correct, expected),
            "top_parsed_values": stats["parsed_values"].most_common(5),
            "top_mismatches": stats["mismatches"].most_common(5),
        }
    return finalized


def finalize_axis_stats(by_hard_axis: dict[str, dict[str, int]]) -> dict[str, dict[str, Any]]:
    finalized: dict[str, dict[str, Any]] = {}
    for axis, stats in sorted(by_hard_axis.items()):
        total = stats["total"]
        field_total = stats["field_total"]
        finalized[axis] = {
            "total": total,
            "winner_correct": stats["winner_correct"],
            "winner_accuracy": safe_div(stats["winner_correct"], total),
            "field_accuracy": safe_div(stats["field_correct"], field_total),
            "full_matches": stats["full_matches"],
            "full_match_rate": safe_div(stats["full_matches"], total),
        }
    return finalized


def rank_samples(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(sample: dict[str, Any]) -> tuple[int, int, int, str]:
        winner_bad = 0 if not sample["winner_correct"] else 1
        field_correct = int(sample["field_correct"])
        confusion_bonus = 0 if sample["schema_confusions"] else 1
        return (winner_bad, field_correct, confusion_bonus, str(sample["pair_id"]))

    return sorted(samples, key=key)


def safe_div(numerator: int | float, denominator: int | float) -> float | None:
    if not denominator:
        return None
    return numerator / denominator


def render_markdown(summaries: list[dict[str, Any]], *, max_samples_per_run: int = 6) -> str:
    lines: list[str] = [
        "# Pairwise v0.1 Compact Generation Mismatch Analysis",
        "",
        "This report inspects raw compact generations and separates winner errors,",
        "missing compact fields, field-value mismatches, and schema confusions.",
        "",
        "## Run Summary",
        "",
        "| run | rows | winner acc | parse fail | avg parsed fields | all fields present | full target match | most missing fields |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for summary in summaries:
        lines.append(
            "| {name} | {total} | {winner_accuracy} | {parse_failure_rate} | {avg_present_fields} | {all_expected_present_rate} | {full_match_rate} | {missing} |".format(
                name=summary["name"],
                total=summary["total"],
                winner_accuracy=format_rate(summary["winner_accuracy"]),
                parse_failure_rate=format_rate(summary["parse_failure_rate"]),
                avg_present_fields=format_number(summary["avg_present_fields"]),
                all_expected_present_rate=format_rate(summary["all_expected_present_rate"]),
                full_match_rate=format_rate(summary["full_match_rate"]),
                missing=format_counter(summary["missing_fields"], 4),
            )
        )
    lines.extend(["", "## Field Accuracy", ""])
    for summary in summaries:
        lines.extend(
            [
                f"### {summary['name']}",
                "",
                "| field | present | present rate | correct | accuracy | top parsed values | top mismatches |",
                "| --- | ---: | ---: | ---: | ---: | --- | --- |",
            ]
        )
        for field, stats in summary["field_stats"].items():
            lines.append(
                "| {field} | {present}/{expected} | {present_rate} | {correct}/{expected} | {accuracy} | {values} | {mismatches} |".format(
                    field=field,
                    present=stats["present"],
                    expected=stats["expected"],
                    present_rate=format_rate(stats["present_rate"]),
                    correct=stats["correct"],
                    accuracy=format_rate(stats["accuracy"]),
                    values=format_value_counts(stats["top_parsed_values"]),
                    mismatches=format_mismatch_counts(stats["top_mismatches"]),
                )
            )
        lines.append("")

    lines.extend(["## Schema Confusions", ""])
    for summary in summaries:
        top = summary["confusions"].most_common(10)
        lines.append(f"### {summary['name']}")
        lines.append("")
        if not top:
            lines.extend(["No schema-level confusion labels were detected.", ""])
            continue
        lines.extend(
            [
                "| field | parsed value | label | count |",
                "| --- | --- | --- | ---: |",
            ]
        )
        for (field, parsed_value, label), count in top:
            lines.append(f"| {field} | {escape_cell(parsed_value)} | {label} | {count} |")
        lines.append("")

    lines.extend(["## By Hard Axis", ""])
    for summary in summaries:
        lines.append(f"### {summary['name']}")
        lines.append("")
        lines.extend(
            [
                "| hard axis | rows | winner acc | field acc | full match |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for axis, stats in summary["by_hard_axis"].items():
            lines.append(
                "| {axis} | {total} | {winner_accuracy} | {field_accuracy} | {full_match_rate} |".format(
                    axis=axis,
                    total=stats["total"],
                    winner_accuracy=format_rate(stats["winner_accuracy"]),
                    field_accuracy=format_rate(stats["field_accuracy"]),
                    full_match_rate=format_rate(stats["full_match_rate"]),
                )
            )
        lines.append("")

    lines.extend(["## Prioritized Samples", ""])
    for summary in summaries:
        lines.append(f"### {summary['name']}")
        lines.append("")
        lines.extend(
            [
                "| pair | expected | predicted | fields | missing | confusions | raw generation |",
                "| --- | --- | --- | ---: | --- | --- | --- |",
            ]
        )
        for sample in summary["samples"][:max_samples_per_run]:
            lines.append(
                "| {pair} | {expected} | {predicted} | {field_correct}/{field_total} | {missing} | {confusions} | {raw} |".format(
                    pair=escape_cell(str(sample["pair_id"])),
                    expected=sample["expected_winner"],
                    predicted=sample["predicted_winner"],
                    field_correct=sample["field_correct"],
                    field_total=sample["field_total"],
                    missing=escape_cell(sample["missing_fields"]),
                    confusions=escape_cell(sample["schema_confusions"]),
                    raw=escape_cell(truncate(sample["raw_generation"], 220)),
                )
            )
        lines.append("")

    lines.extend(
        [
            "## Interpretation",
            "",
            "- Full target match is zero because most runs either omit several expected fields or emit schema-confused values.",
            "- The low-learning-rate adapter and base mostly behave like winner generators, not compact-target generators.",
            "- The `lr1e-5` adapter learned to emit more fields, but many values are not from the expected label space or are copied from field names/action labels.",
            "- This supports redesigning the target/prompt or separating winner selection from metadata-field prediction before more rank-128 LoRA training.",
            "",
        ]
    )
    return "\n".join(lines)


def write_samples_csv(path: Path, summaries: list[dict[str, Any]], *, max_samples_per_run: int = 20) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "run",
        "pair_id",
        "source_id",
        "is_swapped",
        "parse_status",
        "hard_axis",
        "delta_tag",
        "scope_error_direction",
        "expected_winner",
        "predicted_winner",
        "winner_correct",
        "field_correct",
        "field_total",
        "field_accuracy",
        "missing_fields",
        "wrong_fields",
        "schema_confusions",
        "raw_generation",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for summary in summaries:
            for sample in summary["samples"][:max_samples_per_run]:
                writer.writerow({field: sample.get(field) for field in fieldnames})


def format_rate(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.4f}"


def format_number(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}"


def format_counter(counter: Counter[str], limit: int) -> str:
    if not counter:
        return "-"
    return ", ".join(f"{key}:{count}" for key, count in counter.most_common(limit))


def format_value_counts(items: list[tuple[str, int]]) -> str:
    if not items:
        return "-"
    return ", ".join(f"{escape_cell(str(value))}:{count}" for value, count in items)


def format_mismatch_counts(items: list[tuple[tuple[str, str], int]]) -> str:
    if not items:
        return "-"
    return ", ".join(f"{escape_cell(str(exp))}->{escape_cell(str(got))}:{count}" for (exp, got), count in items)


def truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
