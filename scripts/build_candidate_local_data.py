#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if SRC_ROOT.exists():
    sys.path.insert(0, str(SRC_ROOT))

from reconcile_opsd.candidate_local_data import (  # noqa: E402
    build_candidate_local_records,
    candidate_local_manifest,
    write_candidate_local_jsonl,
)
from reconcile_opsd.pairwise_eval import load_pairwise_jsonl  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Build candidate-local ACCEPTABLE/ERROR_TAG examples from pairwise JSONL.")
    parser.add_argument("--dataset", required=True, help="Input pairwise JSONL.")
    parser.add_argument("--output", required=True, help="Output candidate-local JSONL.")
    parser.add_argument("--manifest-output", default="", help="Optional manifest JSON path.")
    args = parser.parse_args()

    pairwise_records = load_pairwise_jsonl(args.dataset)
    records = build_candidate_local_records(pairwise_records)
    write_candidate_local_jsonl(records, args.output)
    manifest = candidate_local_manifest(records, args.dataset, source_pair_count=len(pairwise_records))
    manifest.update(
        {
            "input": args.dataset,
            "output": args.output,
            "manifest_output": args.manifest_output or None,
        }
    )

    if args.manifest_output:
        manifest_path = Path(args.manifest_output)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
