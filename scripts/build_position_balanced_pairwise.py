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

from reconcile_opsd.pairwise_data import build_position_balanced_records, pairwise_manifest, write_pairwise_jsonl
from reconcile_opsd.pairwise_eval import load_pairwise_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Build original/swapped position-balanced pairwise records.")
    parser.add_argument("--input", required=True, help="Input pairwise JSONL.")
    parser.add_argument("--output", required=True, help="Output pairwise JSONL.")
    parser.add_argument("--manifest-output", required=True)
    parser.add_argument("--mode", choices=["both", "original-only", "swapped-only"], default="both")
    args = parser.parse_args()

    records = load_pairwise_jsonl(args.input)
    balanced = build_position_balanced_records(
        records,
        include_original=args.mode in {"both", "original-only"},
        include_swapped=args.mode in {"both", "swapped-only"},
    )
    write_pairwise_jsonl(balanced, args.output)
    manifest = pairwise_manifest(balanced, args.input, set())
    manifest.update(
        {
            "input": args.input,
            "output": args.output,
            "mode": args.mode,
            "source_pair_count": len(records),
            "output_pair_count": len(balanced),
        }
    )
    manifest_path = Path(args.manifest_output)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
