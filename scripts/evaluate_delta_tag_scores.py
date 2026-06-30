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

from reconcile_opsd.delta_tag_eval import evaluate_delta_tag_scores, read_delta_tag_score_rows
from reconcile_opsd.pairwise_eval import load_pairwise_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate constrained DELTA_TAG score rows.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--scores", action="append", required=True, help="Run spec NAME=path/to/scores.jsonl")
    parser.add_argument("--output-md", default="reports/delta_tag_eval.md")
    parser.add_argument("--output-json", default="reports/delta_tag_eval.json")
    parser.add_argument("--output-csv", default="reports/delta_tag_eval_errors.csv")
    args = parser.parse_args()

    records = load_pairwise_jsonl(args.dataset)
    run_results: list[dict[str, Any]] = []
    error_rows: list[dict[str, Any]] = []
    for name, path in parse_specs(args.scores):
        score_rows = read_delta_tag_score_rows(path)
        metrics = evaluate_delta_tag_scores(records, score_rows)
        run_results.append({"name": name, "path": display_path(path), "metrics": metrics})
        for row in metrics["errors"]:
            error_rows.append({"run": name, **row})

    output_md = Path(args.output_md)
    output_json = Path(args.output_json)
    output_csv = Path(args.output_csv)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(render_markdown(run_results), encoding="utf-8")
    output_json.write_text(json.dumps(run_results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_error_csv(output_csv, error_rows)
    print(json.dumps({"runs": [run["name"] for run in run_results], "output_md": str(output_md)}, ensure_ascii=False, indent=2))


def parse_specs(specs: list[str]) -> list[tuple[str, Path]]:
    parsed = []
    for spec in specs:
        if "=" not in spec:
            raise ValueError(f"--scores must be NAME=path, got {spec}")
        name, path = spec.split("=", 1)
        parsed.append((name, Path(path)))
    return parsed


def display_path(path: Path) -> str:
    try:
        return path.as_posix()
    except ValueError:
        return str(path)


def render_markdown(run_results: list[dict[str, Any]]) -> str:
    lines = [
        "# Pairwise DELTA_TAG Constrained Evaluation",
        "",
        "This report scores the rationale tag separately from winner selection. It conditions on the gold winner and therefore measures metadata target alignment, not end-to-end assistant behavior.",
        "",
        "## Summary",
        "",
        "| run | accuracy | missing | top predictions |",
        "| --- | ---: | ---: | --- |",
    ]
    for run in run_results:
        metrics = run["metrics"]
        top_predictions = ", ".join(
            f"{label}:{count}" for label, count in sorted(metrics["predicted_distribution"].items(), key=lambda item: (-item[1], item[0]))[:5]
        )
        lines.append(
            f"| {run['name']} | {format_rate(metrics['correct'], metrics['total'])} | {metrics['missing_scores']} | {top_predictions or '-'} |"
        )
    lines.extend(["", "## By Expected DELTA_TAG", ""])
    for run in run_results:
        lines.extend([f"### {run['name']}", "", "| expected | accuracy | top predicted labels |", "| --- | ---: | --- |"])
        for label, row in sorted(run["metrics"]["by_expected_delta_tag"].items()):
            top = ", ".join(f"{pred}:{count}" for pred, count in sorted(row["predictions"].items(), key=lambda item: (-item[1], item[0]))[:5])
            lines.append(f"| {label} | {format_rate(row['correct'], row['total'])} | {top or '-'} |")
        lines.append("")
    lines.extend(["## By Hard Axis", ""])
    for run in run_results:
        lines.extend([f"### {run['name']}", "", "| hard axis | accuracy |", "| --- | ---: |"])
        for axis, row in sorted(run["metrics"]["by_hard_axis"].items()):
            lines.append(f"| {axis} | {format_rate(row['correct'], row['total'])} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def format_rate(correct: int, total: int) -> str:
    if total == 0:
        return "-"
    return f"{correct}/{total} = {correct / total:.4f}"


def write_error_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "run",
        "pair_id",
        "source_id",
        "expected_delta_tag",
        "predicted_delta_tag",
        "hard_axis",
        "scope_error_direction",
        "winner",
        "delta_tag_margin",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})


if __name__ == "__main__":
    main()
