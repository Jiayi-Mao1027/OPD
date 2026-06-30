#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a short model template/generation smoke test.")
    parser.add_argument("--model", required=True, help="Local HF model path.")
    parser.add_argument("--prompt", default="请判断：用户请求中哪些部分可以安全帮助，哪些部分需要拒绝或澄清？")
    parser.add_argument("--output", default="outputs/smoke/qwen3_8b_smoke.json")
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument("--enable-thinking", action="store_true")
    parser.add_argument("--render-only", action="store_true", help="Only render chat template; do not load model.")
    parser.add_argument("--attn-implementation", default="eager", help="Use eager by default to avoid flash-attn dependency.")
    args = parser.parse_args()

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    messages = [
        {"role": "system", "content": "You are a careful reasoning model for safety and usefulness reconciliation."},
        {"role": "user", "content": args.prompt},
    ]
    rendered = apply_template(tokenizer, messages, args.enable_thinking)

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "prompt": args.prompt,
        "enable_thinking": args.enable_thinking,
        "rendered_prompt": rendered,
        "render_only": args.render_only,
    }

    if not args.render_only:
        dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
        model = AutoModelForCausalLM.from_pretrained(
            args.model,
            torch_dtype=dtype,
            device_map="auto",
            trust_remote_code=True,
            attn_implementation=args.attn_implementation,
        )
        inputs = tokenizer([rendered], return_tensors="pt").to(model.device)
        with torch.inference_mode():
            generated = model.generate(
                **inputs,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        new_tokens = generated[0, inputs["input_ids"].shape[-1] :]
        result["response"] = tokenizer.decode(new_tokens, skip_special_tokens=False)
        if torch.cuda.is_available():
            result["cuda_max_memory_allocated_mb"] = round(torch.cuda.max_memory_allocated() / 1024**2, 2)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "rendered_prompt"}, ensure_ascii=False, indent=2))


def apply_template(tokenizer, messages, enable_thinking: bool) -> str:
    kwargs = {"tokenize": False, "add_generation_prompt": True}
    if enable_thinking:
        kwargs["enable_thinking"] = True
    try:
        return tokenizer.apply_chat_template(messages, **kwargs)
    except TypeError:
        kwargs.pop("enable_thinking", None)
        return tokenizer.apply_chat_template(messages, **kwargs)


if __name__ == "__main__":
    main()

