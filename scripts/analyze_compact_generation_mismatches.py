#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if SRC_ROOT.exists():
    sys.path.insert(0, str(SRC_ROOT))

from reconcile_opsd.compact_mismatch import (
    load_jsonl,
    parse_run_spec,
    render_markdown,
    summarize_generation_run,
    write_samples_csv,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze compact generation field mismatches.")
    parser.add_argument(
        "--generation",
        action="append",
        required=True,
        help="Generation JSONL as name=path. May be provided multiple times.",
    )
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--max-samples-per-run", type=int, default=20)
    args = parser.parse_args()

    summaries = []
    for spec in args.generation:
        run = parse_run_spec(spec)
        rows = load_jsonl(run.path)
        summaries.append(summarize_generation_run(run.name, rows))

    output_md = Path(args.output_md)
    output_json = Path(args.output_json)
    output_csv = Path(args.output_csv)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)

    output_md.write_text(
        render_markdown(summaries, max_samples_per_run=min(args.max_samples_per_run, 10)),
        encoding="utf-8",
    )
    output_json.write_text(json.dumps([to_jsonable(summary) for summary in summaries], indent=2, ensure_ascii=False), encoding="utf-8")
    write_samples_csv(output_csv, summaries, max_samples_per_run=args.max_samples_per_run)


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Counter):
        return [{"key": to_jsonable(key), "count": count} for key, count in value.most_common()]
    if isinstance(value, dict):
        return {str(key): to_jsonable(val) for key, val in value.items() if key != "samples"}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]
    return value


if __name__ == "__main__":
    main()
