#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from reconcile_opsd.schema import ReconcileExample, load_jsonl


SYSTEM_PROMPT = """You are learning Reconcile-OPSD action-mode judgment.
Choose exactly one ACTION_MODE from:
direct_answer, ask_clarification, safe_high_level, safe_redirect, partial_allowed, refuse, continue_reasoning.

Return:
ACTION_MODE: <one mode>
REASON: <one short reason>

Prefer calibrated reconciliation: do not collapse ambiguous or partial-help cases into pure refusal."""


@dataclass
class EncodedExample:
    input_ids: list[int]
    labels: list[int]


class ActionModeDataset(Dataset):
    def __init__(self, examples: list[EncodedExample]):
        self.examples = examples

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> EncodedExample:
        return self.examples[idx]


def main() -> None:
    parser = argparse.ArgumentParser(description="Tiny QLoRA/SFT smoke for action-mode labels.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", default="data/reconcilebench_seed.jsonl")
    parser.add_argument("--output-dir", default="outputs/train_smoke/qwen3_8b_action_lora")
    parser.add_argument("--limit", type=int, default=4)
    parser.add_argument("--max-length", type=int, default=768)
    parser.add_argument("--max-steps", type=int, default=2)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--lora-r", type=int, default=8)
    parser.add_argument("--lora-alpha", type=int, default=16)
    parser.add_argument("--attn-implementation", default="eager")
    parser.add_argument("--no-4bit", action="store_true")
    args = parser.parse_args()

    examples = load_jsonl(args.dataset)
    if args.limit:
        examples = examples[: args.limit]
    if not examples:
        raise ValueError("No training examples selected")

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    quantization_config = None
    if not args.no_4bit:
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

    encoded = [encode_example(tokenizer, example, args.max_length) for example in examples]
    loader = DataLoader(
        ActionModeDataset(encoded),
        batch_size=1,
        shuffle=True,
        collate_fn=lambda batch: collate(batch, tokenizer.pad_token_id),
    )

    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=args.lr)
    losses: list[float] = []
    step = 0
    while step < args.max_steps:
        for batch in loader:
            batch = {key: value.to(model.device) for key, value in batch.items()}
            outputs = model(**batch)
            loss = outputs.loss
            loss.backward()
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            losses.append(float(loss.detach().cpu()))
            step += 1
            print(json.dumps({"step": step, "loss": losses[-1]}, ensure_ascii=False))
            if step >= args.max_steps:
                break

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output_dir / "adapter")
    tokenizer.save_pretrained(output_dir / "tokenizer")
    metrics = {
        "model": args.model,
        "dataset": args.dataset,
        "num_examples": len(examples),
        "max_steps": args.max_steps,
        "losses": losses,
        "load_in_4bit": not args.no_4bit,
        "output_dir": str(output_dir),
    }
    if torch.cuda.is_available():
        metrics["cuda_max_memory_allocated_mb"] = round(torch.cuda.max_memory_allocated() / 1024**2, 2)
    (output_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


def encode_example(tokenizer, example: ReconcileExample, max_length: int) -> EncodedExample:
    prompt_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_content(example.prompt)},
    ]
    prompt = apply_template(tokenizer, prompt_messages)
    target = f"ACTION_MODE: {example.action_mode}\nREASON: {example.judgment_delta}{tokenizer.eos_token}"
    prompt_ids = tokenizer(prompt, add_special_tokens=False).input_ids
    target_ids = tokenizer(target, add_special_tokens=False).input_ids
    input_ids = (prompt_ids + target_ids)[:max_length]
    labels = ([-100] * len(prompt_ids) + target_ids)[:max_length]
    if all(label == -100 for label in labels):
        raise ValueError(f"target was truncated away for {example.id}")
    return EncodedExample(input_ids=input_ids, labels=labels)


def build_user_content(prompt: str) -> str:
    return (
        "User request:\n"
        f"{prompt}\n\n"
        "Choose the best response mode for this request. "
        "Be especially careful not to over-refuse benign, ambiguous, or partial-help cases."
    )


def apply_template(tokenizer, messages: list[dict[str, str]]) -> str:
    kwargs = {"tokenize": False, "add_generation_prompt": True, "enable_thinking": False}
    try:
        return tokenizer.apply_chat_template(messages, **kwargs)
    except TypeError:
        kwargs.pop("enable_thinking", None)
        return tokenizer.apply_chat_template(messages, **kwargs)


def collate(batch: list[EncodedExample], pad_token_id: int) -> dict[str, torch.Tensor]:
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

