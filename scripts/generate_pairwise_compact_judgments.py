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

from reconcile_opsd.compact_generation import (
    COMPACT_PROMPT_STYLES,
    compact_structured_target,
    compact_generation_system_prompt,
    compare_compact_fields,
    expected_compact_fields,
    parse_compact_judgment,
    parse_errors_for_compact_judgment,
    parsed_fields_for_output,
    parsed_winner,
)
from reconcile_opsd.pairwise_eval import load_pairwise_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and parse compact pairwise judgment targets.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=0, help="0 means all records.")
    parser.add_argument("--adapter", default="", help="Optional PEFT adapter path.")
    parser.add_argument("--load-in-4bit", action="store_true")
    parser.add_argument("--attn-implementation", default="eager")
    parser.add_argument("--enable-thinking", action="store_true")
    parser.add_argument("--prompt-style", choices=COMPACT_PROMPT_STYLES, default="minimal")
    parser.add_argument("--max-new-tokens", type=int, default=96)
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
    system_prompt = compact_generation_system_prompt(args.prompt_style)
    with output.open("w", encoding="utf-8") as handle:
        for record in records:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": record["input"]},
            ]
            rendered, template_supports_enable_thinking = apply_template(tokenizer, messages, args.enable_thinking)
            generated_text, token_count = generate_text(model, tokenizer, rendered, input_device, args.max_new_tokens)
            parsed = parse_compact_judgment(generated_text)
            predicted = parsed_winner(parsed)
            parse_errors = parse_errors_for_compact_judgment(parsed)
            expected_fields = expected_compact_fields(record)
            field_comparison = compare_compact_fields(expected_fields, parsed)
            expected = record["winner"]
            output_record = {
                "pair_id": record["pair_id"],
                "id": record["pair_id"],
                "source_id": record["source_id"],
                "source_split": record["source_split"],
                "expected_winner": expected,
                "predicted_winner": predicted or "invalid",
                "correct": predicted == expected,
                "winner_margin": None,
                "scores": {},
                "gold_action_mode": record.get("gold_action_mode"),
                "primary_action": record.get("primary_action"),
                "negative_action": record.get("negative_action"),
                "delta_tag": record["delta_tag"],
                "hard_axis": record.get("hard_axis"),
                "scope_error_direction": record.get("scope_error_direction"),
                "score_mode": "compact_structured_generation",
                "generation_mode": "greedy_compact_structured_judgment",
                "prompt_style": args.prompt_style,
                "raw_generation": generated_text,
                "generated_text": generated_text,
                "parse_status": "ok" if not parse_errors else "failed",
                "parse_errors": parse_errors,
                "parsed": parsed_fields_for_output(parsed),
                "parsed_fields": parsed,
                "expected_fields": expected_fields,
                "expected_compact_target": compact_structured_target(record),
                "field_matches": field_comparison["by_field"],
                "field_comparison": field_comparison,
                "parse_failure": predicted is None,
                "generated_token_count": token_count,
                "max_new_tokens": args.max_new_tokens,
                "do_sample": False,
                "model": args.model,
                "adapter": args.adapter or None,
                "adapter_base_model_name_or_path": adapter_metadata.get("base_model_name_or_path"),
                "load_in_4bit": args.load_in_4bit,
                "requested_enable_thinking": args.enable_thinking,
                "template_supports_enable_thinking": template_supports_enable_thinking,
                "attn_implementation": args.attn_implementation,
                "input_device": str(input_device),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            handle.write(json.dumps(output_record, ensure_ascii=False) + "\n")
            handle.flush()
            print(json.dumps({"pair_id": record["pair_id"], "expected": expected, "predicted": predicted or "invalid"}, ensure_ascii=False))

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


def read_adapter_metadata(adapter: str) -> dict[str, object]:
    if not adapter:
        return {}
    config_path = Path(adapter) / "adapter_config.json"
    if not config_path.exists():
        return {"adapter_config_missing": True}
    with config_path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    return {
        "base_model_name_or_path": config.get("base_model_name_or_path"),
        "target_modules": config.get("target_modules"),
        "r": config.get("r"),
        "lora_alpha": config.get("lora_alpha"),
    }


def apply_template(tokenizer: Any, messages: list[dict[str, str]], enable_thinking: bool) -> tuple[str, bool]:
    kwargs: dict[str, Any] = {"tokenize": False, "add_generation_prompt": True, "enable_thinking": enable_thinking}
    try:
        return tokenizer.apply_chat_template(messages, **kwargs), True
    except TypeError:
        kwargs.pop("enable_thinking", None)
        return tokenizer.apply_chat_template(messages, **kwargs), False


def generate_text(model: Any, tokenizer: Any, prompt: str, input_device: torch.device, max_new_tokens: int) -> tuple[str, int]:
    inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=False).to(input_device)
    with torch.inference_mode():
        generated = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    new_tokens = generated[0, inputs["input_ids"].shape[-1] :]
    text = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    return text, int(new_tokens.shape[0])


if __name__ == "__main__":
    main()
