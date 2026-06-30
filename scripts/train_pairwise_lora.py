#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from reconcile_opsd.gpu_utils import gpu_report, query_gpu_status
from reconcile_opsd.pairwise_eval import load_pairwise_jsonl


SYSTEM_PROMPT = """You are learning Reconcile-OPSD pairwise judgment.
Choose which decision card is better for the user request.

Prefer the card that best preserves safety boundaries, useful allowed help,
clarification when needed, and fork-state when final action is premature.

Return the requested target format exactly."""


@dataclass
class EncodedPairwiseExample:
    input_ids: list[int]
    labels: list[int]


class PairwiseDataset(Dataset):
    def __init__(self, examples: list[EncodedPairwiseExample]):
        self.examples = examples

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> EncodedPairwiseExample:
        return self.examples[idx]


def main() -> None:
    parser = argparse.ArgumentParser(description="Rank-128 LoRA/SFT smoke for pairwise judgment-delta targets.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", default="data/pairwise/reconcilebench_v0_1_train_pairwise.jsonl")
    parser.add_argument("--output-dir", default="outputs/train_pairwise_smoke/qwen3_8b_pairwise_lora")
    parser.add_argument("--limit", type=int, default=0, help="0 means all training pairs.")
    parser.add_argument("--max-length", type=int, default=2048)
    parser.add_argument("--max-steps", type=int, default=20, help="Number of optimizer steps.")
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=1)
    parser.add_argument(
        "--target-style",
        choices=["winner_only", "structured_judgment_delta", "compact_structured_judgment"],
        default="structured_judgment_delta",
    )
    parser.add_argument("--render-samples", type=int, default=8, help="Save this many rendered prompt/target examples for audit.")
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--lora-r", type=int, default=128)
    parser.add_argument("--lora-alpha", type=int, default=256)
    parser.add_argument("--attn-implementation", default="eager")
    parser.add_argument("--load-in-4bit", action="store_true", help="Use only for explicit QLoRA experiments; default is rank-128 LoRA without quantization.")
    parser.add_argument("--no-4bit", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--min-free-mb", type=int, default=20_000)
    parser.add_argument("--max-used-mb", type=int, default=70_000)
    args = parser.parse_args()

    records = load_pairwise_jsonl(args.dataset)
    if args.limit:
        records = records[: args.limit]
    if not records:
        raise ValueError("No training records selected")
    if args.batch_size < 1:
        raise ValueError("--batch-size must be at least 1")
    if args.gradient_accumulation_steps < 1:
        raise ValueError("--gradient-accumulation-steps must be at least 1")
    load_in_4bit = bool(args.load_in_4bit and not args.no_4bit)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_preflight(output_dir / "preflight_gpu.json", args)
    write_resolved_config(output_dir / "config_resolved.json", args, len(records))

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    write_render_samples(output_dir / "render_samples.jsonl", tokenizer, records, args.target_style, args.render_samples)

    quantization_config = None
    if load_in_4bit:
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
        trust_remote_code=True,
        attn_implementation=args.attn_implementation,
        quantization_config=quantization_config,
    )
    if quantization_config is not None:
        model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora_config)
    model.train()
    input_device = model.get_input_embeddings().weight.device

    encoded = [encode_record(tokenizer, record, args.max_length, args.target_style) for record in records]
    loader = DataLoader(
        PairwiseDataset(encoded),
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=lambda batch: collate(batch, tokenizer.pad_token_id),
    )

    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=args.lr)
    losses: list[float] = []
    losses_path = output_dir / "train_losses.jsonl"
    step = 0
    micro_step = 0
    with losses_path.open("w", encoding="utf-8") as loss_handle:
        while step < args.max_steps:
            for batch in loader:
                batch = {key: value.to(input_device) for key, value in batch.items()}
                outputs = model(**batch)
                raw_loss = outputs.loss
                (raw_loss / args.gradient_accumulation_steps).backward()
                micro_step += 1
                raw_loss_value = float(raw_loss.detach().cpu())
                if micro_step % args.gradient_accumulation_steps == 0:
                    optimizer.step()
                    optimizer.zero_grad(set_to_none=True)
                    step += 1
                    losses.append(raw_loss_value)
                    row = {
                        "step": step,
                        "micro_step": micro_step,
                        "loss": raw_loss_value,
                        "batch_size": args.batch_size,
                        "gradient_accumulation_steps": args.gradient_accumulation_steps,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    loss_handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                    loss_handle.flush()
                    print(json.dumps(row, ensure_ascii=False))
                    if step >= args.max_steps:
                        break

    model.save_pretrained(output_dir / "adapter")
    tokenizer.save_pretrained(output_dir / "tokenizer")
    metrics = {
        "model": args.model,
        "dataset": args.dataset,
        "num_records": len(records),
        "max_steps": args.max_steps,
        "batch_size": args.batch_size,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "effective_batch_size": args.batch_size * args.gradient_accumulation_steps,
        "target_style": args.target_style,
        "render_samples": args.render_samples,
        "losses": losses,
        "first_loss": losses[0] if losses else None,
        "last_loss": losses[-1] if losses else None,
        "load_in_4bit": load_in_4bit,
        "output_dir": str(output_dir),
        "adapter": str(output_dir / "adapter"),
        "input_device": str(input_device),
    }
    if torch.cuda.is_available():
        metrics["cuda_max_memory_allocated_mb"] = round(torch.cuda.max_memory_allocated() / 1024**2, 2)
    (output_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


def write_preflight(path: Path, args: argparse.Namespace) -> None:
    try:
        rows = query_gpu_status()
        payload: dict[str, Any] = gpu_report(rows, min_free_mb=args.min_free_mb, max_used_mb=args.max_used_mb)
    except Exception as exc:
        payload = {"error": str(exc)}
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_resolved_config(path: Path, args: argparse.Namespace, num_records: int) -> None:
    payload = {
        "model": args.model,
        "dataset": args.dataset,
        "num_records": num_records,
        "max_length": args.max_length,
        "max_steps": args.max_steps,
        "batch_size": args.batch_size,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "effective_batch_size": args.batch_size * args.gradient_accumulation_steps,
        "target_style": args.target_style,
        "render_samples": args.render_samples,
        "lr": args.lr,
        "lora_r": args.lora_r,
        "lora_alpha": args.lora_alpha,
        "attn_implementation": args.attn_implementation,
        "load_in_4bit": bool(args.load_in_4bit and not args.no_4bit),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def encode_record(tokenizer: Any, record: dict[str, Any], max_length: int, target_style: str) -> EncodedPairwiseExample:
    prompt, target = render_training_record(tokenizer, record, target_style)
    prompt_ids = tokenizer(prompt, add_special_tokens=False).input_ids
    target_ids = tokenizer(target, add_special_tokens=False).input_ids
    input_ids = (prompt_ids + target_ids)[:max_length]
    labels = ([-100] * len(prompt_ids) + target_ids)[:max_length]
    if all(label == -100 for label in labels):
        raise ValueError(f"target was truncated away for {record['pair_id']}")
    return EncodedPairwiseExample(input_ids=input_ids, labels=labels)


def render_training_record(tokenizer: Any, record: dict[str, Any], target_style: str) -> tuple[str, str]:
    prompt_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": record["input"]},
    ]
    prompt = apply_template(tokenizer, prompt_messages)
    target = build_target(record, target_style, tokenizer.eos_token)
    return prompt, target


def build_target(record: dict[str, Any], target_style: str, eos_token: str) -> str:
    if target_style == "winner_only":
        target = f"WINNER: {record['winner']}"
    elif target_style == "structured_judgment_delta":
        target = record["target"]
    elif target_style == "compact_structured_judgment":
        target = compact_structured_target(record)
    else:
        raise ValueError(f"unknown target_style: {target_style}")
    return f"{target}{eos_token}"


def compact_structured_target(record: dict[str, Any]) -> str:
    lines = [
        f"WINNER: {record['winner']}",
        f"GOLD_ACTION: {record.get('gold_action_mode', record.get('gold_action', ''))}",
        f"HARD_AXIS: {record.get('hard_axis', 'other')}",
        f"DELTA_TAG: {record['delta_tag']}",
    ]
    direction = record.get("scope_error_direction")
    if isinstance(direction, str) and direction:
        lines.append(f"SCOPE_ERROR_DIRECTION: {direction}")
    judgment = record.get("gold_judgment")
    if isinstance(judgment, dict):
        granularity = judgment.get("required_granularity")
        if isinstance(granularity, str) and granularity:
            lines.append(f"REQUIRED_GRANULARITY: {granularity}")
        fork_policy = judgment.get("fork_policy")
        if isinstance(fork_policy, str) and fork_policy:
            lines.append(f"FORK_POLICY: {fork_policy}")
    return "\n".join(lines)


def write_render_samples(path: Path, tokenizer: Any, records: list[dict[str, Any]], target_style: str, limit: int) -> None:
    if limit <= 0:
        return
    with path.open("w", encoding="utf-8") as handle:
        for record in records[:limit]:
            prompt, target = render_training_record(tokenizer, record, target_style)
            row = {
                "pair_id": record["pair_id"],
                "source_id": record["source_id"],
                "winner": record["winner"],
                "target_style": target_style,
                "prompt": prompt,
                "target": target,
            }
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def apply_template(tokenizer: Any, messages: list[dict[str, str]]) -> str:
    kwargs = {"tokenize": False, "add_generation_prompt": True, "enable_thinking": False}
    try:
        return tokenizer.apply_chat_template(messages, **kwargs)
    except TypeError:
        kwargs.pop("enable_thinking", None)
        return tokenizer.apply_chat_template(messages, **kwargs)


def collate(batch: list[EncodedPairwiseExample], pad_token_id: int) -> dict[str, torch.Tensor]:
    max_len = max(len(example.input_ids) for example in batch)
    input_ids = []
    attention_mask = []
    labels = []
    for example in batch:
        pad_len = max_len - len(example.input_ids)
        input_ids.append(example.input_ids + [pad_token_id] * pad_len)
        attention_mask.append([1] * len(example.input_ids) + [0] * pad_len)
        labels.append(example.labels + [-100] * pad_len)
    return {
        "input_ids": torch.tensor(input_ids, dtype=torch.long),
        "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
        "labels": torch.tensor(labels, dtype=torch.long),
    }


if __name__ == "__main__":
    main()
