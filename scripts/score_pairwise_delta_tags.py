#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if SRC_ROOT.exists():
    sys.path.insert(0, str(SRC_ROOT))

from reconcile_opsd.compact_generation import DELTA_TAG_ORDER, format_allowed_labels
from reconcile_opsd.pairwise_eval import load_pairwise_jsonl
from score_pairwise_judgments import apply_template, read_adapter_metadata, score_candidate


SYSTEM_PROMPT = f"""You are evaluating Reconcile-OPSD pairwise rationale tags.
The user request and two decision cards are given. The better card is provided.

Return only:
DELTA_TAG: <delta label>

Use only one of these labels:
{format_allowed_labels(DELTA_TAG_ORDER)}"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Constrained logprob scoring for pairwise DELTA_TAG labels.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=0, help="0 means all records.")
    parser.add_argument("--adapter", default="", help="Optional PEFT adapter path.")
    parser.add_argument("--load-in-4bit", action="store_true")
    parser.add_argument("--attn-implementation", default="eager")
    parser.add_argument("--enable-thinking", action="store_true")
    args = parser.parse_args()

    records = load_pairwise_jsonl(args.dataset)
    if args.limit:
        records = records[: args.limit]

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = load_model(args)
    input_device = model.get_input_embeddings().weight.device
    adapter_metadata = read_adapter_metadata(args.adapter)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for record in records:
            user_prompt = f"{record['input']}\n\nKnown better card: {record['winner']}"
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
            rendered, template_supports_enable_thinking = apply_template(tokenizer, messages, args.enable_thinking)
            scores = {
                tag: score_candidate(model, tokenizer, rendered, f"DELTA_TAG: {tag}", input_device)
                for tag in DELTA_TAG_ORDER
            }
            predicted = max(scores, key=lambda tag: scores[tag]["avg_logprob"])
            expected = record["delta_tag"]
            runner_up = max((tag for tag in scores if tag != expected), key=lambda tag: scores[tag]["avg_logprob"])
            margin = scores[expected]["avg_logprob"] - scores[runner_up]["avg_logprob"]
            output_record = {
                "pair_id": record["pair_id"],
                "id": record["pair_id"],
                "source_id": record["source_id"],
                "source_split": record["source_split"],
                "expected_delta_tag": expected,
                "predicted_delta_tag": predicted,
                "correct": predicted == expected,
                "delta_tag_margin": margin,
                "conditioned_winner": record["winner"],
                "gold_action_mode": record.get("gold_action_mode"),
                "primary_action": record.get("primary_action"),
                "negative_action": record.get("negative_action"),
                "hard_axis": record.get("hard_axis"),
                "scope_error_direction": record.get("scope_error_direction"),
                "scores": scores,
                "model": args.model,
                "adapter": args.adapter or None,
                "adapter_base_model_name_or_path": adapter_metadata.get("base_model_name_or_path"),
                "load_in_4bit": args.load_in_4bit,
                "score_mode": "delta_tag_constrained",
                "requested_enable_thinking": args.enable_thinking,
                "template_supports_enable_thinking": template_supports_enable_thinking,
                "attn_implementation": args.attn_implementation,
                "input_device": str(input_device),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            handle.write(json.dumps(output_record, ensure_ascii=False) + "\n")
            handle.flush()
            print(
                json.dumps(
                    {
                        "pair_id": record["pair_id"],
                        "expected": expected,
                        "predicted": predicted,
                        "margin": round(margin, 4),
                    },
                    ensure_ascii=False,
                )
            )

    if torch.cuda.is_available():
        print(json.dumps({"cuda_max_memory_allocated_mb": round(torch.cuda.max_memory_allocated() / 1024**2, 2)}, ensure_ascii=False))


def load_model(args: argparse.Namespace):
    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    quantization_config = None
    if args.load_in_4bit:
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=dtype,
        device_map="auto",
        trust_remote_code=True,
        attn_implementation=args.attn_implementation,
        quantization_config=quantization_config,
    )
    if args.adapter:
        try:
            from peft import PeftModel
        except ImportError as exc:
            raise RuntimeError("Loading --adapter requires peft to be installed") from exc
        model = PeftModel.from_pretrained(model, args.adapter)
    model.eval()
    return model


if __name__ == "__main__":
    main()
