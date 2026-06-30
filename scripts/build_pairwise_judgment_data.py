#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from reconcile_opsd.pairwise_data import (
    build_pairwise_records,
    example_ids,
    pairwise_manifest,
    prompt_hashes,
    read_score_rows,
    write_pairwise_jsonl,
)
from reconcile_opsd.schema import load_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Build pairwise judgment-delta records from ReconcileBench examples.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", default="data/pairwise/reconcilebench_v0_train_pairwise.jsonl")
    parser.add_argument("--manifest-output", default="data/pairwise/reconcilebench_v0_train_pairwise_manifest.json")
    parser.add_argument("--split-name", default="train")
    parser.add_argument("--max-pairs-per-example", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20260630)
    parser.add_argument("--score-file", default="", help="Optional constrained-score JSONL for choosing hard confusers.")
    parser.add_argument(
        "--forbid-source-dataset",
        action="append",
        default=[],
        help="Dataset whose ids must not appear in generated source_example_id values, e.g. dev split.",
    )
    args = parser.parse_args()

    examples = load_jsonl(args.dataset)
    forbidden_ids: set[str] = set()
    forbidden_prompt_hashes: set[str] = set()
    for forbidden_path in args.forbid_source_dataset:
        forbidden_examples = load_jsonl(forbidden_path)
        forbidden_ids.update(example_ids(forbidden_examples))
        forbidden_prompt_hashes.update(prompt_hashes(forbidden_examples))
    source_ids = example_ids(examples)
    overlap = sorted(source_ids & forbidden_ids)
    if overlap:
        raise ValueError(f"dataset contains forbidden source ids: {', '.join(overlap)}")
    prompt_overlap = sorted(prompt_hashes(examples) & forbidden_prompt_hashes)
    if prompt_overlap:
        raise ValueError(f"dataset contains forbidden prompt hashes: {', '.join(prompt_overlap)}")

    score_rows = read_score_rows(args.score_file) if args.score_file else None
    records = build_pairwise_records(
        examples,
        split_name=args.split_name,
        max_pairs_per_example=args.max_pairs_per_example,
        seed=args.seed,
        score_rows=score_rows,
    )
    write_pairwise_jsonl(records, args.output)
    manifest = pairwise_manifest(records, args.dataset, forbidden_ids)
    manifest.update(
        {
            "split_name": args.split_name,
            "max_pairs_per_example": args.max_pairs_per_example,
            "seed": args.seed,
            "score_file": args.score_file or None,
            "forbid_source_datasets": args.forbid_source_dataset,
            "forbidden_prompt_hash_overlap": sorted({record["prompt_hash"] for record in records} & forbidden_prompt_hashes),
        }
    )
    manifest_path = Path(args.manifest_output)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": args.output, "manifest": args.manifest_output, **manifest}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
