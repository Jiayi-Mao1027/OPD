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

from reconcile_opsd.dataset_tools import audit_examples
from reconcile_opsd.schema import load_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit ReconcileBench dataset balance and coverage.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    examples = load_jsonl(args.dataset)
    report = audit_examples(examples)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    print(payload, end="")
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")


if __name__ == "__main__":
    main()
