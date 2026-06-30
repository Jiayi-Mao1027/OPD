#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if SRC_ROOT.exists():
    sys.path.insert(0, str(SRC_ROOT))

from reconcile_opsd.pairwise_eval import evaluate_pairwise_scores, load_pairwise_jsonl, read_pairwise_score_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate pairwise judgment-delta score rows.")
    parser.add_argument("--dataset", required=True, help="Pairwise JSONL dataset.")
    parser.add_argument("--scores", action="append", required=True, help="Run spec NAME=path/to/scores.jsonl")
    parser.add_argument("--output-md", default="reports/pairwise_v0_eval.md")
    parser.add_argument("--output-json", default="reports/pairwise_v0_eval.json")
    parser.add_argument("--output-csv", default="reports/pairwise_v0_errors.csv")
    args = parser.parse_args()

    records = load_pairwise_jsonl(args.dataset)
    run_results: list[dict[str, Any]] = []
    error_rows: list[dict[str, Any]] = []
    for name, path in parse_specs(args.scores):
        score_rows = read_pairwise_score_rows(path)
        metrics = evaluate_pairwise_scores(records, score_rows)
        run_results.append({"name": name, "path": display_path(path), "metrics": metrics})
        for row in metrics["errors"]:
            error_rows.append({"run": name, **row})

    output_md = Path(args.output_md)
    output_json = Path(args.output_json)
    output_csv = Path(args.output_csv)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(render_markdown(args.dataset, run_results), encoding="utf-8")
    output_json.write_text(json.dumps(run_results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_errors(output_csv, error_rows)
    print(json.dumps({"runs": [run["name"] for run in run_results], "output_md": str(output_md), "output_json": str(output_json), "output_csv": str(output_csv)}, ensure_ascii=False, indent=2))


def parse_specs(specs: list[str]) -> list[tuple[str, Path]]:
    parsed: list[tuple[str, Path]] = []
    for spec in specs:
        if "=" not in spec:
            raise ValueError(f"expected NAME=path spec, got: {spec}")
        name, path = spec.split("=", 1)
        if not name.strip() or not path.strip():
            raise ValueError(f"invalid run spec: {spec}")
        parsed.append((name.strip(), Path(path.strip())))
    return parsed


def display_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def render_markdown(dataset: str, run_results: list[dict[str, Any]]) -> str:
    lines = [
        "# Pairwise Judgment-Delta Eval",
        "",
        f"Dataset: `{dataset}`",
        "",
    ]
    if uses_compact_structured_score(run_results):
        lines.extend(
            [
                "Caveat: this report uses `score-mode=compact_structured_judgment` for at least one run. It is a label-conditioned target-alignment diagnostic because the scored continuation includes gold metadata fields. Use `winner_only` reports for the primary pairwise acceptance gate.",
                "",
            ]
        )
    lines.extend(
        [
        "## Summary",
        "",
        "| run | total | missing | parse fail | winner acc | fork acc | scope acc | pred A | pred B | A recall | B recall | swap consistency | bias gate | avg winner margin |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
        ]
    )
    for run in run_results:
        metrics = run["metrics"]
        lines.append(
            f"| {run['name']} | {metrics['total']} | {metrics['missing_scores']} | {metrics['parse_failures']} | {format_metric(metrics['winner_accuracy'])} | {format_metric(metrics['fork_preservation_accuracy'])} | {format_metric(metrics['scope_contract_accuracy'])} | {format_metric(metrics['pred_A_rate'])} | {format_metric(metrics['pred_B_rate'])} | {format_metric(metrics['A_recall'])} | {format_metric(metrics['B_recall'])} | {format_metric(metrics['swap_consistency'])} | {metrics['position_bias_gate']['status']} | {format_metric(metrics['average_winner_margin'])} |"
        )
    lines.extend(
        [
            "",
            "## Bias / Collapse Summary",
            "",
            "| run | gold A/B | pred A/B | majority side | majority rate | A-rate delta | side entropy | min side acc | collapse |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for run in run_results:
        metrics = run["metrics"]
        side_bias = metrics["side_bias"]
        gold_counts = metrics["gold_winner_counts"]
        pred_counts = metrics["predicted_winner_counts"]
        lines.append(
            f"| {run['name']} | {gold_counts.get('A', 0)}/{gold_counts.get('B', 0)} | {pred_counts.get('A', 0)}/{pred_counts.get('B', 0)} | {side_bias['predicted_majority_side']} | {format_metric(side_bias['predicted_majority_rate'])} | {format_metric(side_bias['predicted_a_rate_minus_gold_a_rate'])} | {format_metric(side_bias['side_entropy_bits'])} | {format_metric(side_bias['min_expected_side_accuracy'])} | {metrics['position_bias_gate']['status']} |"
        )
    if uses_compact_field_metrics(run_results):
        lines.extend(
            [
                "",
                "## Compact Field Summary",
                "",
                "| run | examples | field acc | full target match |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for run in run_results:
            metrics = run["metrics"]
            lines.append(
                f"| {run['name']} | {metrics.get('compact_field_examples', 0)} | {format_metric(metrics.get('compact_field_accuracy'))} | {format_metric(metrics.get('compact_field_full_match_rate'))} |"
            )
    for run in run_results:
        metrics = run["metrics"]
        lines.extend(["", f"## {run['name']}", "", f"Source: `{run['path']}`", "", "### By Delta Tag", ""])
        lines.extend(render_group_table(metrics["by_delta_tag"]))
        lines.extend(["", "### By Expected Winner Side", ""])
        lines.extend(render_group_table(metrics["by_expected_side"]))
        lines.extend(["", "### By Hard Axis", ""])
        lines.extend(render_group_table(metrics["by_hard_axis"]))
        lines.extend(["", "### By Scope Error Direction", ""])
        lines.extend(render_group_table(metrics["by_scope_error_direction"]))
        lines.extend(["", "### By Gold Action Mode", ""])
        lines.extend(render_group_table(metrics["by_gold_action_mode"]))
        lines.extend(["", "### By Source Id", ""])
        lines.extend(render_group_table(metrics["by_source_id"]))
        if metrics.get("compact_field_examples"):
            lines.extend(["", "### By Compact Field", ""])
            lines.extend(render_group_table(metrics["by_compact_field"]))
        lines.extend(["", "### Swap Diagnostics", ""])
        lines.extend(render_swap_diagnostics(metrics.get("swap_diagnostics", {})))
        lines.extend(["", "### Confusion Matrix", "", "```json", json.dumps(metrics["confusion_matrix"], ensure_ascii=False, indent=2), "```"])
    lines.append("")
    return "\n".join(lines)


def uses_compact_structured_score(run_results: list[dict[str, Any]]) -> bool:
    for run in run_results:
        score_modes = run["metrics"].get("score_mode_counts", {})
        if isinstance(score_modes, dict) and score_modes.get("compact_structured_judgment"):
            return True
        if "compactscore" in run["name"]:
            return True
    return False


def uses_compact_field_metrics(run_results: list[dict[str, Any]]) -> bool:
    return any(bool(run["metrics"].get("compact_field_examples")) for run in run_results)


def render_group_table(group: dict[str, dict[str, float | int]]) -> list[str]:
    lines = ["| group | total | correct | acc |", "| --- | ---: | ---: | ---: |"]
    for name, stats in group.items():
        lines.append(f"| {name} | {stats['total']} | {stats['correct']} | {format_metric(stats['accuracy'])} |")
    return lines


def render_swap_diagnostics(swap_diagnostics: object) -> list[str]:
    if not isinstance(swap_diagnostics, dict) or not swap_diagnostics.get("comparable"):
        return ["No comparable original/swapped pairs in this dataset."]
    lines = [
        f"Comparable original/swapped parents: `{swap_diagnostics['comparable']}`; inconsistent: `{swap_diagnostics['inconsistent']}`; consistency: `{format_metric(swap_diagnostics['consistency'])}`.",
        "",
    ]
    inconsistent = swap_diagnostics.get("inconsistent_rows")
    if not isinstance(inconsistent, list) or not inconsistent:
        lines.append("No inconsistent swapped pairs.")
        return lines
    lines.extend(
        [
            "| parent pair | axis | delta | scope direction | original pred | swapped pred | original margin | swapped margin | near tie |",
            "| --- | --- | --- | --- | --- | --- | ---: | ---: | --- |",
        ]
    )
    for row in inconsistent:
        if not isinstance(row, dict):
            continue
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("parent_pair_id", "")),
                    str(row.get("hard_axis", "")),
                    str(row.get("delta_tag", "")),
                    str(row.get("scope_error_direction", "")),
                    f"{row.get('original_expected', '')}->{row.get('original_predicted', '')}",
                    f"{row.get('swapped_expected', '')}->{row.get('swapped_predicted', '')}",
                    format_metric(row.get("original_margin")),
                    format_metric(row.get("swapped_margin")),
                    str(row.get("near_tie", "")),
                ]
            )
            + " |"
        )
    return lines


def format_metric(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, (int, float)):
        return f"{value:.4f}"
    return str(value)


def write_errors(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = [
        "run",
        "pair_id",
        "source_id",
        "source_split",
        "expected_winner",
        "predicted_winner",
        "winner_margin",
        "candidate_a_action",
        "candidate_b_action",
        "chosen_action",
        "gold_action_mode",
        "primary_action",
        "negative_action",
        "delta_tag",
        "hard_axis",
        "scope_error_direction",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            clean = dict(row)
            if isinstance(clean.get("winner_margin"), float):
                clean["winner_margin"] = f"{clean['winner_margin']:.6f}"
            writer.writerow(clean)


if __name__ == "__main__":
    main()
