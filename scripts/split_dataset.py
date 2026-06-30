#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from reconcile_opsd.dataset_tools import audit_examples, make_action_mode_split, write_examples
from reconcile_opsd.schema import load_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Create deterministic train/dev splits for ReconcileBench.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output-dir", default="data/splits")
    parser.add_argument("--name", default="")
    parser.add_argument("--dev-ratio", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=20260630)
    args = parser.parse_args()

    examples = load_jsonl(args.dataset)
    train, dev = make_action_mode_split(examples, dev_ratio=args.dev_ratio, seed=args.seed)

    dataset_name = args.name or Path(args.dataset).stem
    output_dir = Path(args.output_dir)
    train_path = output_dir / f"{dataset_name}_train.jsonl"
    dev_path = output_dir / f"{dataset_name}_dev.jsonl"
    manifest_path = output_dir / f"{dataset_name}_manifest.json"

    write_examples(train, train_path)
    write_examples(dev, dev_path)

    manifest = {
        "dataset": args.dataset,
        "seed": args.seed,
        "dev_ratio": args.dev_ratio,
        "train_path": str(train_path),
        "dev_path": str(dev_path),
        "train_audit": audit_examples(train),
        "dev_audit": audit_examples(dev),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
