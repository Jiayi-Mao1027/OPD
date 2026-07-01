#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if SRC_ROOT.exists():
    sys.path.insert(0, str(SRC_ROOT))

from reconcile_opsd.gpu_utils import gpu_report, query_gpu_status
from reconcile_opsd.schema import ReconcileExample, load_jsonl


SYSTEM_PROMPT = """You are a careful assistant for safety-sensitive and ambiguous user requests.
Answer the user directly when safe. When the request mixes allowed and disallowed content, help with the allowed part and avoid operationally harmful details. Preserve uncertainty and multiple plausible explanations when evidence is insufficient. Do not reveal hidden labels or evaluation metadata."""


@dataclass(frozen=True)
class EncodedResponseExample:
    input_ids: list[int]
    labels: list[int]


class ResponseDataset:
    def __init__(self, examples: list[EncodedResponseExample]):
        self.examples = examples

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> EncodedResponseExample:
        return self.examples[idx]


def main() -> None:
    parser = argparse.ArgumentParser(description="Rank-128 BF16 LoRA SFT for ReconcileBench assistant final responses.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", default="data/splits/reconcilebench_v0_1_train.jsonl")
    parser.add_argument("--output-dir", default="outputs/train_response_lora/qwen3_8b_v0_1_response_r128")
    parser.add_argument("--limit", type=int, default=0, help="0 means all training examples.")
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument("--max-steps", type=int, default=24, help="Number of optimizer steps.")
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=8)
    parser.add_argument("--target-style", choices=["final_response"], default="final_response")
    parser.add_argument("--prompt-style", choices=["direct"], default="direct")
    parser.add_argument("--lr", type=float, default=3e-6)
    parser.add_argument("--lora-r", type=int, default=128)
    parser.add_argument("--lora-alpha", type=int, default=256)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument("--attn-implementation", default="eager")
    parser.add_argument("--render-samples", type=int, default=8, help="Save this many rendered prompt/target examples for audit.")
    parser.add_argument("--min-free-mb", type=int, default=20_000)
    parser.add_argument("--max-used-mb", type=int, default=70_000)
    parser.add_argument("--gradient-checkpointing", action="store_true")
    parser.add_argument("--render-only", action="store_true", help="Write config/render samples, then exit before loading the model.")
    args = parser.parse_args()

    if args.lora_r != 128:
        raise ValueError("This project phase is constrained to rank-128 LoRA; set --lora-r 128.")
    if args.batch_size < 1:
        raise ValueError("--batch-size must be at least 1")
    if args.gradient_accumulation_steps < 1:
        raise ValueError("--gradient-accumulation-steps must be at least 1")

    examples = load_jsonl(args.dataset)
    if args.limit:
        examples = examples[: args.limit]
    if not examples:
        raise ValueError("No training examples selected")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_preflight(output_dir / "preflight_gpu.json", args)
    write_resolved_config(output_dir / "config_resolved.json", args, len(examples))

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    write_render_samples(output_dir / "render_samples.jsonl", tokenizer, examples, args.render_samples, args.prompt_style)
    if args.render_only:
        return

    import torch
    from peft import LoraConfig, get_peft_model
    from torch.utils.data import DataLoader
    from transformers import AutoModelForCausalLM

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
        trust_remote_code=True,
        attn_implementation=args.attn_implementation,
    )
    if args.gradient_checkpointing:
        model.gradient_checkpointing_enable()

    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora_config)
    model.train()
    input_device = model.get_input_embeddings().weight.device

    encoded = [encode_example(tokenizer, example, args.max_length, args.prompt_style) for example in examples]
    loader = DataLoader(
        ResponseDataset(encoded),
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=lambda batch: collate(batch, tokenizer.pad_token_id),
    )

    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=args.lr)
    optimizer.zero_grad(set_to_none=True)
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
        "num_examples": len(examples),
        "max_steps": args.max_steps,
        "batch_size": args.batch_size,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "effective_batch_size": args.batch_size * args.gradient_accumulation_steps,
        "max_length": args.max_length,
        "target_style": args.target_style,
        "prompt_style": args.prompt_style,
        "lr": args.lr,
        "lora_r": args.lora_r,
        "lora_alpha": args.lora_alpha,
        "lora_dropout": args.lora_dropout,
        "load_in_4bit": False,
        "full_parameter_finetune": False,
        "gradient_checkpointing": args.gradient_checkpointing,
        "losses": losses,
        "first_loss": losses[0] if losses else None,
        "last_loss": losses[-1] if losses else None,
        "output_dir": str(output_dir),
        "adapter": str(output_dir / "adapter"),
        "input_device": str(input_device),
        "parameter_report": trainable_parameter_report(model),
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


def write_resolved_config(path: Path, args: argparse.Namespace, num_examples: int) -> None:
    payload = {
        "model": args.model,
        "dataset": args.dataset,
        "num_examples": num_examples,
        "max_length": args.max_length,
        "max_steps": args.max_steps,
        "batch_size": args.batch_size,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "effective_batch_size": args.batch_size * args.gradient_accumulation_steps,
        "target_style": args.target_style,
        "prompt_style": args.prompt_style,
        "lr": args.lr,
        "lora_r": args.lora_r,
        "lora_alpha": args.lora_alpha,
        "lora_dropout": args.lora_dropout,
        "attn_implementation": args.attn_implementation,
        "load_in_4bit": False,
        "full_parameter_finetune": False,
        "gradient_checkpointing": args.gradient_checkpointing,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def encode_example(tokenizer: Any, example: ReconcileExample, max_length: int, prompt_style: str = "direct") -> EncodedResponseExample:
    prompt, target = render_training_example(tokenizer, example, prompt_style)
    prompt_ids = tokenizer(prompt, add_special_tokens=False).input_ids
    target_ids = tokenizer(target, add_special_tokens=False).input_ids
    input_ids = (prompt_ids + target_ids)[:max_length]
    labels = ([-100] * len(prompt_ids) + target_ids)[:max_length]
    if all(label == -100 for label in labels):
        raise ValueError(f"target was truncated away for {example.id}")
    return EncodedResponseExample(input_ids=input_ids, labels=labels)


def render_training_example(tokenizer: Any, example: ReconcileExample, prompt_style: str = "direct") -> tuple[str, str]:
    messages = build_messages(example.prompt, prompt_style)
    prompt = apply_template(tokenizer, messages)
    target = build_target(example, tokenizer.eos_token)
    return prompt, target


def build_messages(user_prompt: str, prompt_style: str = "direct") -> list[dict[str, str]]:
    if prompt_style != "direct":
        raise ValueError(f"unknown prompt style: {prompt_style}")
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def build_target(example: ReconcileExample, eos_token: str | None) -> str:
    return f"{example.final_response.strip()}{eos_token or ''}"


def write_render_samples(path: Path, tokenizer: Any, examples: list[ReconcileExample], limit: int, prompt_style: str = "direct") -> None:
    if limit <= 0:
        return
    with path.open("w", encoding="utf-8") as handle:
        for example in examples[:limit]:
            prompt, target = render_training_example(tokenizer, example, prompt_style)
            row = {
                "id": example.id,
                "prompt": prompt,
                "target": target,
                "prompt_style": prompt_style,
                "target_style": "final_response",
                "action_mode": example.action_mode,
                "primary_action": example.primary_action or example.action_mode,
                "acceptable_actions": example.acceptable_actions or [example.primary_action or example.action_mode],
            }
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def apply_template(tokenizer: Any, messages: list[dict[str, str]]) -> str:
    kwargs: dict[str, Any] = {"tokenize": False, "add_generation_prompt": True, "enable_thinking": False}
    try:
        return tokenizer.apply_chat_template(messages, **kwargs)
    except TypeError:
        kwargs.pop("enable_thinking", None)
        return tokenizer.apply_chat_template(messages, **kwargs)


def collate(batch: list[EncodedResponseExample], pad_token_id: int) -> dict[str, Any]:
    import torch

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


def trainable_parameter_report(model: Any) -> dict[str, Any]:
    trainable = 0
    total = 0
    for parameter in model.parameters():
        count = parameter.numel()
        total += count
        if parameter.requires_grad:
            trainable += count
    return {
        "trainable_parameters": trainable,
        "total_parameters": total,
        "trainable_fraction": trainable / total if total else None,
    }


if __name__ == "__main__":
    main()
