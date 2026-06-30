#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from reconcile_opsd.action_metrics import evaluate_action_predictions, normalize_prediction
from reconcile_opsd.schema import ACTION_MODE_ORDER, TERMINAL_ACTION_MODES, load_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare action-mode prediction and constrained-score runs.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--predictions", action="append", default=[], help="Run spec NAME=path/to/predictions.jsonl")
    parser.add_argument("--scores", action="append", default=[], help="Run spec NAME=path/to/scores.jsonl")
    parser.add_argument("--output-md", default="reports/reconcile_v0_eval_base_vs_qlora.md")
    parser.add_argument("--output-csv", default="reports/reconcile_v0_error_table.csv")
    parser.add_argument("--output-json", default="")
    parser.add_argument("--exclude-continue-reasoning", action="store_true")
    args = parser.parse_args()

    examples = load_jsonl(args.dataset)
    run_results: list[dict[str, Any]] = []
    item_rows: list[dict[str, Any]] = []

    for name, path in parse_specs(args.predictions):
        predictions = read_prediction_file(path)
        result = evaluate_action_predictions(
            examples,
            predictions,
            exclude_continue_reasoning=args.exclude_continue_reasoning,
        )
        run_results.append({"name": name, "kind": "predictions", "path": str(path), "metrics": result})
        item_rows.extend(error_rows(name, result))

    for name, path in parse_specs(args.scores):
        score_rows = read_score_file(path)
        result = evaluate_action_predictions(
            examples,
            {},
            score_rows=score_rows,
            candidate_modes=TERMINAL_ACTION_MODES if args.exclude_continue_reasoning else ACTION_MODE_ORDER,
            exclude_continue_reasoning=args.exclude_continue_reasoning,
        )
        run_results.append({"name": name, "kind": "scores", "path": str(path), "metrics": result})
        item_rows.extend(error_rows(name, result))

    if not run_results:
        raise SystemExit("provide at least one --predictions or --scores spec")

    output_md = Path(args.output_md)
    output_csv = Path(args.output_csv)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(render_markdown(args.dataset, run_results), encoding="utf-8")
    write_error_csv(output_csv, item_rows)
    if args.output_json:
        output_json = Path(args.output_json)
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(run_results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"runs": [run["name"] for run in run_results], "output_md": str(output_md), "output_csv": str(output_csv)}, ensure_ascii=False, indent=2))


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


def read_prediction_file(path: Path) -> dict[str, str]:
    predictions: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            item_id = record.get("id")
            if not isinstance(item_id, str):
                raise ValueError(f"{path}:{line_no}: expected string id")
            response = record.get("response")
            predicted = record.get("predicted_action_mode")
            if isinstance(predicted, str):
                predictions[item_id] = predicted
            elif isinstance(response, str):
                predictions[item_id] = response
            else:
                raise ValueError(f"{path}:{line_no}: expected response or predicted_action_mode")
    return predictions


def read_score_file(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            item_id = record.get("id")
            if not isinstance(item_id, str):
                raise ValueError(f"{path}:{line_no}: expected string id")
            rows[item_id] = record
    return rows


def render_markdown(dataset: str, run_results: list[dict[str, Any]]) -> str:
    lines = [
        "# ReconcileBench Action-Mode Eval",
        "",
        f"Dataset: `{dataset}`",
        "",
        "## Summary",
        "",
        "| run | kind | total | acc | allowed acc | macro-F1 | top-2 allowed | avg gold margin | avg entropy |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for run in run_results:
        metrics = run["metrics"]
        lines.append(
            "| {name} | {kind} | {total} | {acc} | {allowed} | {macro} | {top2} | {margin} | {entropy} |".format(
                name=run["name"],
                kind=run["kind"],
                total=metrics["total"],
                acc=format_metric(metrics["accuracy"]),
                allowed=format_metric(metrics["allowed_set_accuracy"]),
                macro=format_metric(metrics["macro_f1"]),
                top2=format_metric(metrics["top2_allowed_set_accuracy"]),
                margin=format_metric(metrics["average_gold_margin"]),
                entropy=format_metric(metrics["average_entropy"]),
            )
        )

    for run in run_results:
        metrics = run["metrics"]
        lines.extend(
            [
                "",
                f"## {run['name']}",
                "",
                f"Source: `{run['path']}`",
                "",
                "### Per-Mode F1",
                "",
                "| mode | support | precision | recall | F1 |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for mode in ACTION_MODE_ORDER:
            stats = metrics["per_mode"][mode]
            lines.append(
                f"| {mode} | {stats['support']} | {format_metric(stats['precision'])} | {format_metric(stats['recall'])} | {format_metric(stats['f1'])} |"
            )
        lines.extend(["", "### Hard-Boundary Confusions", ""])
        if metrics["hard_boundary_confusions"]:
            for error_type, count in sorted(metrics["hard_boundary_confusions"].items()):
                lines.append(f"- `{error_type}`: {count}")
        else:
            lines.append("- none")
        lines.extend(["", "### Confusion Matrix", ""])
        lines.append("```json")
        lines.append(json.dumps(metrics["confusion_matrix"], ensure_ascii=False, indent=2))
        lines.append("```")

    lines.append("")
    return "\n".join(lines)


def format_metric(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, (int, float)):
        return f"{value:.4f}"
    return str(value)


def error_rows(run_name: str, result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in result["items"]:
        if item["correct"]:
            continue
        rows.append(
            {
                "run": run_name,
                "id": item["id"],
                "gold": item["gold"],
                "predicted": item["predicted"],
                "acceptable_actions": ";".join(item["acceptable_actions"]),
                "top_modes": ";".join(item["top_modes"]),
                "gold_margin": "" if item["gold_margin"] is None else f"{item['gold_margin']:.6f}",
                "entropy": "" if item["entropy"] is None else f"{item['entropy']:.6f}",
                "error_type": item["error_type"],
                "predicted_normalized": normalize_prediction(item["predicted"]),
            }
        )
    return rows


def write_error_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = [
        "run",
        "id",
        "gold",
        "predicted",
        "acceptable_actions",
        "top_modes",
        "gold_margin",
        "entropy",
        "error_type",
        "predicted_normalized",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
