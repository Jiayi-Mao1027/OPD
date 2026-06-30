#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from reconcile_opsd.pairwise_eval import load_pairwise_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit pairwise judgment-delta data for ambiguity and schema gaps.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-csv", required=True)
    args = parser.parse_args()

    records = load_pairwise_jsonl(args.dataset)
    rows = [audit_record(record) for record in records]
    summary = summarize(rows)

    output_md = Path(args.output_md)
    output_json = Path(args.output_json)
    output_csv = Path(args.output_csv)
    for path in [output_md, output_json, output_csv]:
        path.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(render_markdown(args.dataset, summary), encoding="utf-8")
    output_json.write_text(json.dumps({"dataset": args.dataset, "summary": summary, "rows": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(output_csv, rows)
    print(json.dumps({"dataset": args.dataset, "records": len(records), "output_md": str(output_md), "output_json": str(output_json), "output_csv": str(output_csv)}, ensure_ascii=False, indent=2))


def audit_record(record: dict[str, Any]) -> dict[str, Any]:
    acceptable = set(record.get("acceptable_actions") or [])
    action_a = candidate_action(record.get("candidate_a"))
    action_b = candidate_action(record.get("candidate_b"))
    issues: list[str] = []
    if action_a in acceptable and action_b in acceptable:
        issues.append("both_candidates_acceptable")
    if record.get("builder_version") == "pairwise_v0_1":
        for field in ["hard_axis", "gold_judgment"]:
            if not record.get(field):
                issues.append(f"missing_{field}")
        if record.get("delta_tag") == "lost_fork_state" and record.get("hard_axis") != "fork_state":
            issues.append("lost_fork_not_hard_axis")
        if record.get("delta_tag") == "wrong_scope":
            if record.get("hard_axis") != "scope_contract":
                issues.append("wrong_scope_not_scope_axis")
            if record.get("scope_error_direction") in {None, "", "none"}:
                issues.append("wrong_scope_missing_direction")
    status = "clean"
    if any(issue.startswith("missing_") or issue.endswith("_axis") or issue.endswith("_direction") for issue in issues):
        status = "taxonomy_problem"
    elif issues:
        status = "ambiguous"
    return {
        "pair_id": record["pair_id"],
        "source_id": record["source_id"],
        "builder_version": record.get("builder_version", ""),
        "gold_action": record.get("gold_action", record.get("gold_action_mode", "")),
        "negative_action": record.get("negative_action", ""),
        "delta_tag": record.get("delta_tag", ""),
        "hard_axis": record.get("hard_axis", ""),
        "scope_error_direction": record.get("scope_error_direction", ""),
        "status": status,
        "issues": ";".join(issues),
    }


def candidate_action(value: object) -> str:
    if not isinstance(value, dict):
        return ""
    action = value.get("action_mode")
    return action if isinstance(action, str) else ""


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total": len(rows),
        "status_counts": dict(sorted(Counter(row["status"] for row in rows).items())),
        "delta_tag_counts": dict(sorted(Counter(row["delta_tag"] for row in rows).items())),
        "hard_axis_counts": dict(sorted(Counter(row["hard_axis"] for row in rows).items())),
        "scope_error_direction_counts": dict(sorted(Counter(row["scope_error_direction"] for row in rows).items())),
    }


def render_markdown(dataset: str, summary: dict[str, Any]) -> str:
    lines = [
        "# Pairwise Data Audit",
        "",
        f"Dataset: `{dataset}`",
        "",
        f"Total pairs: `{summary['total']}`",
        "",
        "## Status Counts",
        "",
    ]
    lines.extend(render_count_table(summary["status_counts"]))
    lines.extend(["", "## Delta Tag Counts", ""])
    lines.extend(render_count_table(summary["delta_tag_counts"]))
    lines.extend(["", "## Hard Axis Counts", ""])
    lines.extend(render_count_table(summary["hard_axis_counts"]))
    lines.extend(["", "## Scope Error Direction Counts", ""])
    lines.extend(render_count_table(summary["scope_error_direction_counts"]))
    lines.append("")
    return "\n".join(lines)


def render_count_table(counts: dict[str, int]) -> list[str]:
    lines = ["| group | count |", "| --- | ---: |"]
    for name, count in counts.items():
        lines.append(f"| {name or '(empty)'} | {count} |")
    return lines


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = [
        "pair_id",
        "source_id",
        "builder_version",
        "gold_action",
        "negative_action",
        "delta_tag",
        "hard_axis",
        "scope_error_direction",
        "status",
        "issues",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


if __name__ == "__main__":
    main()
