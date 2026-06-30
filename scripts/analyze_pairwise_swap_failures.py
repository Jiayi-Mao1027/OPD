#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if SRC_ROOT.exists():
    sys.path.insert(0, str(SRC_ROOT))

from reconcile_opsd.pairwise_eval import load_pairwise_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze parent-level position-swap failures from pairwise eval JSON.")
    parser.add_argument("--eval-json", required=True, help="JSON written by scripts/evaluate_pairwise_scores.py")
    parser.add_argument("--dataset", required=True, help="Position-balanced pairwise JSONL used for the eval.")
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-csv", required=True)
    args = parser.parse_args()

    run_results = load_eval_json(args.eval_json)
    records = load_pairwise_jsonl(args.dataset)
    parent_context = build_parent_context(records)
    analysis = analyze(run_results, parent_context, display_path(args.eval_json), display_path(args.dataset))

    output_md = Path(args.output_md)
    output_json = Path(args.output_json)
    output_csv = Path(args.output_csv)
    for path in [output_md, output_json, output_csv]:
        path.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(render_markdown(analysis), encoding="utf-8")
    output_json.write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(output_csv, analysis["inconsistent_rows"])
    print(
        json.dumps(
            {
                "runs": [run["name"] for run in analysis["runs"]],
                "output_md": str(output_md),
                "output_json": str(output_json),
                "output_csv": str(output_csv),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def load_eval_json(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"{path}: expected list of run results")
    for index, run in enumerate(payload):
        if not isinstance(run, dict) or not isinstance(run.get("metrics"), dict) or not isinstance(run.get("name"), str):
            raise ValueError(f"{path}: invalid run result at index {index}")
    return payload


def build_parent_context(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    context: dict[str, dict[str, Any]] = {}
    for record in records:
        parent = record.get("parent_pair_id")
        variant = record.get("position_variant")
        if not isinstance(parent, str) or variant != "original":
            continue
        context[parent] = {
            "prompt": record.get("prompt", ""),
            "source_id": record.get("source_id", ""),
            "gold_action": record.get("gold_action", record.get("gold_action_mode", "")),
            "negative_action": record.get("negative_action", ""),
            "hard_axis": record.get("hard_axis", ""),
            "delta_tag": record.get("delta_tag", ""),
            "scope_error_direction": record.get("scope_error_direction", ""),
            "candidate_a_action": candidate_action(record.get("candidate_a")),
            "candidate_b_action": candidate_action(record.get("candidate_b")),
            "candidate_a_sketch": candidate_sketch(record.get("candidate_a")),
            "candidate_b_sketch": candidate_sketch(record.get("candidate_b")),
        }
    return context


def analyze(
    run_results: list[dict[str, Any]],
    parent_context: dict[str, dict[str, Any]],
    eval_json: str,
    dataset: str,
) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    all_inconsistent: list[dict[str, Any]] = []
    inconsistent_sets: dict[str, set[str]] = {}
    for run in run_results:
        name = str(run["name"])
        metrics = run["metrics"]
        swap = metrics.get("swap_diagnostics") if isinstance(metrics, dict) else {}
        rows = swap.get("rows", []) if isinstance(swap, dict) else []
        if not isinstance(rows, list):
            rows = []
        enriched_rows = [enrich_swap_row(name, row, parent_context) for row in rows if isinstance(row, dict)]
        inconsistent = [row for row in enriched_rows if not row["consistent"]]
        all_inconsistent.extend(inconsistent)
        inconsistent_sets[name] = {row["parent_pair_id"] for row in inconsistent}
        runs.append(
            {
                "name": name,
                "winner_accuracy": metrics.get("winner_accuracy"),
                "swap_consistency": metrics.get("swap_consistency"),
                "gate_status": (metrics.get("position_bias_gate") or {}).get("status"),
                "comparable": int((swap or {}).get("comparable", 0)),
                "consistent": int((swap or {}).get("consistent", 0)),
                "inconsistent": int((swap or {}).get("inconsistent", len(inconsistent))),
                "inconsistent_by_hard_axis": count_by(inconsistent, "hard_axis"),
                "inconsistent_by_delta_tag": count_by(inconsistent, "delta_tag"),
                "inconsistent_by_scope_error_direction": count_by(inconsistent, "scope_error_direction"),
                "inconsistent_by_locked_prediction": count_by(inconsistent, "locked_prediction"),
                "inconsistent_by_correctness_pattern": count_by(inconsistent, "correctness_pattern"),
                "inconsistent_by_source_id": count_by(inconsistent, "source_id"),
            }
        )

    names = [run["name"] for run in runs]
    persistent = sorted(set.intersection(*(inconsistent_sets[name] for name in names))) if names else []
    baseline = names[0] if names else ""
    cross_run = {
        "baseline": baseline,
        "persistent_inconsistent_parent_ids": persistent,
        "persistent_inconsistent_count": len(persistent),
        "fixed_vs_baseline": {},
        "new_inconsistent_vs_baseline": {},
    }
    if baseline:
        base_set = inconsistent_sets[baseline]
        for name in names[1:]:
            cross_run["fixed_vs_baseline"][name] = sorted(base_set - inconsistent_sets[name])
            cross_run["new_inconsistent_vs_baseline"][name] = sorted(inconsistent_sets[name] - base_set)

    return {
        "eval_json": eval_json,
        "dataset": dataset,
        "runs": runs,
        "cross_run": cross_run,
        "inconsistent_rows": all_inconsistent,
    }


def enrich_swap_row(run_name: str, row: dict[str, Any], parent_context: dict[str, dict[str, Any]]) -> dict[str, Any]:
    parent = str(row.get("parent_pair_id", ""))
    context = parent_context.get(parent, {})
    original_pred = str(row.get("original_predicted", ""))
    swapped_pred = str(row.get("swapped_predicted", ""))
    original_correct = bool(row.get("original_correct"))
    swapped_correct = bool(row.get("swapped_correct"))
    return {
        "run": run_name,
        "parent_pair_id": parent,
        "source_id": str(row.get("source_id") or context.get("source_id", "")),
        "hard_axis": str(row.get("hard_axis") or context.get("hard_axis", "")),
        "delta_tag": str(row.get("delta_tag") or context.get("delta_tag", "")),
        "scope_error_direction": str(row.get("scope_error_direction") or context.get("scope_error_direction", "")),
        "gold_action": str(context.get("gold_action", "")),
        "negative_action": str(context.get("negative_action", "")),
        "locked_prediction": original_pred if original_pred == swapped_pred else "not_locked",
        "correctness_pattern": correctness_pattern(original_correct, swapped_correct),
        "original_expected": str(row.get("original_expected", "")),
        "original_predicted": original_pred,
        "original_correct": original_correct,
        "original_chosen_action": str(row.get("original_chosen_action", "")),
        "swapped_expected": str(row.get("swapped_expected", "")),
        "swapped_predicted": swapped_pred,
        "swapped_correct": swapped_correct,
        "swapped_chosen_action": str(row.get("swapped_chosen_action", "")),
        "consistent": bool(row.get("consistent")),
        "both_wrong": bool(row.get("both_wrong")),
        "candidate_a_action": str(context.get("candidate_a_action", "")),
        "candidate_b_action": str(context.get("candidate_b_action", "")),
        "prompt": str(context.get("prompt", "")),
        "candidate_a_sketch": str(context.get("candidate_a_sketch", "")),
        "candidate_b_sketch": str(context.get("candidate_b_sketch", "")),
    }


def correctness_pattern(original_correct: bool, swapped_correct: bool) -> str:
    if original_correct and swapped_correct:
        return "both_correct"
    if original_correct:
        return "original_only_correct"
    if swapped_correct:
        return "swapped_only_correct"
    return "both_wrong"


def candidate_action(value: object) -> str:
    if isinstance(value, dict) and isinstance(value.get("action_mode"), str):
        return value["action_mode"]
    return ""


def candidate_sketch(value: object) -> str:
    if isinstance(value, dict) and isinstance(value.get("response_sketch"), str):
        return value["response_sketch"]
    return ""


def count_by(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(field, "")) for row in rows).items()))


def render_markdown(analysis: dict[str, Any]) -> str:
    lines = [
        "# Pairwise Swap-Failure Analysis",
        "",
        f"Dataset: `{analysis['dataset']}`",
        "",
        f"Eval JSON: `{analysis['eval_json']}`",
        "",
        "## Run Summary",
        "",
        "| run | winner acc | swap consistency | gate | comparable | inconsistent | locked A | locked B | top inconsistent axes |",
        "| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for run in analysis["runs"]:
        locked = run["inconsistent_by_locked_prediction"]
        axes = compact_counts(run["inconsistent_by_hard_axis"])
        lines.append(
            f"| {run['name']} | {format_metric(run['winner_accuracy'])} | {format_metric(run['swap_consistency'])} | "
            f"{run['gate_status']} | {run['comparable']} | {run['inconsistent']} | "
            f"{locked.get('A', 0)} | {locked.get('B', 0)} | {axes} |"
        )
    lines.extend(["", "## Inconsistent Parents By Run", ""])
    for run in analysis["runs"]:
        lines.extend([f"### {run['name']}", ""])
        lines.extend(render_count_table("Hard axis", run["inconsistent_by_hard_axis"]))
        lines.extend(render_count_table("Scope direction", run["inconsistent_by_scope_error_direction"]))
        lines.extend(render_count_table("Correctness pattern", run["inconsistent_by_correctness_pattern"]))
        lines.extend([""])
    cross = analysis["cross_run"]
    lines.extend(
        [
            "## Cross-Run Delta",
            "",
            f"Baseline: `{cross['baseline']}`",
            "",
            f"Persistent inconsistent parents across all runs: `{cross['persistent_inconsistent_count']}`",
            "",
        ]
    )
    for name, fixed in cross["fixed_vs_baseline"].items():
        new = cross["new_inconsistent_vs_baseline"].get(name, [])
        lines.append(f"- `{name}` fixes `{len(fixed)}` baseline inconsistent parents and adds `{len(new)}` new inconsistent parents.")
    lines.extend(["", "## Failure Samples", ""])
    rows = list(analysis["inconsistent_rows"])[:30]
    if not rows:
        lines.append("No inconsistent parent pairs.")
    else:
        lines.extend(
            [
                "| run | parent | axis | scope | locked | pattern | source | prompt |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in rows:
            lines.append(
                "| "
                + " | ".join(
                    [
                        row["run"],
                        row["parent_pair_id"],
                        row["hard_axis"],
                        row["scope_error_direction"],
                        row["locked_prediction"],
                        row["correctness_pattern"],
                        row["source_id"],
                        one_line(row["prompt"], 90),
                    ]
                )
                + " |"
            )
    lines.append("")
    return "\n".join(lines)


def render_count_table(title: str, counts: dict[str, int]) -> list[str]:
    lines = [f"{title}:", "", "| group | count |", "| --- | ---: |"]
    for name, count in counts.items():
        lines.append(f"| {name or '(empty)'} | {count} |")
    lines.append("")
    return lines


def compact_counts(counts: dict[str, int], limit: int = 3) -> str:
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return ", ".join(f"{name}:{count}" for name, count in ordered[:limit])


def one_line(value: str, limit: int) -> str:
    text = " ".join(str(value).split())
    text = text.replace("|", "/")
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def format_metric(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, (int, float)):
        return f"{value:.4f}"
    return str(value)


def display_path(path: str | Path) -> str:
    return str(path).replace("\\", "/")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = [
        "run",
        "parent_pair_id",
        "source_id",
        "hard_axis",
        "delta_tag",
        "scope_error_direction",
        "gold_action",
        "negative_action",
        "locked_prediction",
        "correctness_pattern",
        "original_expected",
        "original_predicted",
        "original_correct",
        "original_chosen_action",
        "swapped_expected",
        "swapped_predicted",
        "swapped_correct",
        "swapped_chosen_action",
        "candidate_a_action",
        "candidate_b_action",
        "prompt",
        "candidate_a_sketch",
        "candidate_b_sketch",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


if __name__ == "__main__":
    main()
