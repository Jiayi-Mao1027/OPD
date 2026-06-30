#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from reconcile_opsd.heuristic_eval import evaluate_action_modes
from reconcile_opsd.schema import load_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate action-mode predictions with a simple heuristic classifier.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--predictions", required=True, help="JSONL with id and response fields.")
    parser.add_argument("--output", default="outputs/eval/action_mode_eval.json")
    args = parser.parse_args()

    examples = load_jsonl(args.dataset)
    predictions = read_predictions(args.predictions)
    result = evaluate_action_modes(examples, predictions)
    payload = {
        "total": result.total,
        "action_mode_accuracy": result.action_mode_accuracy,
        "expected_counts": result.expected_counts,
        "predicted_counts": result.predicted_counts,
        "mismatches": result.mismatches,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def read_predictions(path: str) -> dict[str, str]:
    predictions: dict[str, str] = {}
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record.get("id"), str) or not isinstance(record.get("response"), str):
                raise ValueError(f"{path}:{line_no}: expected string id and response")
            predictions[record["id"]] = record["response"]
    return predictions


if __name__ == "__main__":
    main()

