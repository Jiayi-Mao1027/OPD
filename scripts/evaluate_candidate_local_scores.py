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

from reconcile_opsd.candidate_local_eval import (
    evaluate_candidate_local_scores,
    load_candidate_local_jsonl,
    read_candidate_local_score_rows,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate candidate-local Reconcile-OPSD score rows.")
    parser.add_argument("--dataset", required=True, help="Candidate-local JSONL dataset.")
    parser.add_argument("--scores", action="append", required=True, help="Run spec NAME=path/to/scores.jsonl")
    parser.add_argument("--output-md", default="reports/candidate_local_eval.md")
    parser.add_argument("--output-json", default="reports/candidate_local_eval.json")
    parser.add_argument("--output-csv", default="reports/candidate_local_errors.csv")
    args = parser.parse_args()

    records = load_candidate_local_jsonl(args.dataset)
    run_results: list[dict[str, Any]] = []
    error_rows: list[dict[str, Any]] = []
    for name, path in parse_specs(args.scores):
        score_rows = read_candidate_local_score_rows(path)
        metrics = evaluate_candidate_local_scores(records, score_rows)
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
        "# Candidate-Local Reconciliation Eval",
        "",
        f"Dataset: `{dataset}`",
        "",
        "Caveat: candidate-local scoring is a reconciliation-scoring diagnostic. Assistant-facing transfer still needs response-selection or generation audits.",
        "",
        "## Summary",
        "",
        "| run | candidates | missing | acceptable acc | acceptable macro-F1 | error-tag acc | error-tag macro-F1 | induced winner acc | swap consistency | avg induced margin |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for run in run_results:
        metrics = run["metrics"]
        induced = metrics.get("induced_pairwise", {})
        lines.append(
            f"| {run['name']} | {metrics['total']} | {metrics['missing_scores']} | {fmt(metrics['acceptable_accuracy'])} | {fmt(metrics['acceptable_macro_f1'])} | {fmt(metrics['error_tag_accuracy'])} | {fmt(metrics['error_tag_macro_f1'])} | {fmt(induced.get('winner_accuracy'))} | {fmt(induced.get('swap_consistency'))} | {fmt(induced.get('average_winner_margin'))} |"
        )
    for run in run_results:
        metrics = run["metrics"]
        induced = metrics.get("induced_pairwise", {})
        lines.extend(["", f"## {run['name']}", "", f"Source: `{run['path']}`", ""])
        lines.extend(["### Candidate Labels", ""])
        lines.extend(render_group_table("Expected Acceptable", metrics["by_expected_acceptable"]))
        lines.extend([""])
        lines.extend(render_group_table("Expected Error Tag", metrics["by_expected_error_tag"]))
        lines.extend(["", "### Candidate Strata", ""])
        lines.extend(render_group_table("Hard Axis", metrics["by_hard_axis"]))
        lines.extend(["", "### Induced Pairwise", ""])
        lines.append(f"- Winner accuracy: `{fmt(induced.get('winner_accuracy'))}`")
        lines.append(f"- Swap consistency: `{fmt(induced.get('swap_consistency'))}`")
        lines.append(f"- Position-bias gate: `{induced.get('position_bias_gate', {}).get('status', '-') if isinstance(induced.get('position_bias_gate'), dict) else '-'}`")
        if isinstance(induced.get("by_hard_axis"), dict):
            lines.extend(["", "#### Induced By Hard Axis", ""])
            lines.extend(render_group_table("Hard Axis", induced["by_hard_axis"]))
        if metrics["errors"]:
            lines.extend(["", "### Candidate Error Samples", ""])
            lines.extend(
                [
                    "| candidate | pair | side | expected acceptable | predicted acceptable | expected tag | predicted tag | hard axis |",
                    "| --- | --- | --- | --- | --- | --- | --- | --- |",
                ]
            )
            for row in metrics["errors"][:25]:
                lines.append(
                    f"| {row.get('candidate_id')} | {row.get('pair_id')} | {row.get('candidate_side')} | {row.get('expected_acceptable')} | {row.get('predicted_acceptable')} | {row.get('expected_error_tag')} | {row.get('predicted_error_tag')} | {row.get('hard_axis')} |"
                )
    lines.append("")
    return "\n".join(lines)


def render_group_table(label: str, group: dict[str, dict[str, Any]]) -> list[str]:
    lines = [f"#### {label}", "", "| group | total | correct | acc |", "| --- | ---: | ---: | ---: |"]
    for name, stats in group.items():
        lines.append(f"| {name} | {stats['total']} | {stats['correct']} | {fmt(stats['accuracy'])} |")
    return lines


def fmt(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, (int, float)):
        return f"{value:.4f}"
    return str(value)


def write_errors(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = [
        "run",
        "candidate_id",
        "pair_id",
        "source_id",
        "candidate_side",
        "expected_acceptable",
        "predicted_acceptable",
        "expected_error_tag",
        "predicted_error_tag",
        "acceptable_margin",
        "error_tag_margin",
        "hard_axis",
        "pair_delta_tag",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            clean = dict(row)
            for field in ["acceptable_margin", "error_tag_margin"]:
                if isinstance(clean.get(field), float):
                    clean[field] = f"{clean[field]:.6f}"
            writer.writerow(clean)


if __name__ == "__main__":
    main()
