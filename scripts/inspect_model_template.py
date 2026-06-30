#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from transformers import AutoTokenizer


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect model config and chat template.")
    parser.add_argument("--model", required=True, help="Local HF model path.")
    parser.add_argument("--output", help="Optional JSON output path.")
    parser.add_argument("--enable-thinking", action="store_true", help="Try tokenizer enable_thinking=True.")
    args = parser.parse_args()

    model_path = Path(args.model)
    config = _read_json(model_path / "config.json")
    tokenizer_config = _read_json(model_path / "tokenizer_config.json")
    template = tokenizer_config.get("chat_template") or ""

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    messages = [
        {"role": "system", "content": "You are evaluating reasoning and safety judgment behavior."},
        {"role": "user", "content": "用户请求有一部分可能有风险，请先判断哪些部分可以安全帮助。"},
    ]
    render_kwargs = {
        "tokenize": False,
        "add_generation_prompt": True,
    }
    if args.enable_thinking:
        render_kwargs["enable_thinking"] = True
    try:
        rendered = tokenizer.apply_chat_template(messages, **render_kwargs)
        render_error = None
    except TypeError as exc:
        render_kwargs.pop("enable_thinking", None)
        rendered = tokenizer.apply_chat_template(messages, **render_kwargs)
        render_error = f"enable_thinking unsupported: {exc}"

    result = {
        "model": str(model_path),
        "model_type": config.get("model_type"),
        "architectures": config.get("architectures"),
        "max_position_embeddings": config.get("max_position_embeddings"),
        "torch_dtype": config.get("torch_dtype"),
        "tokenizer_class": tokenizer_config.get("tokenizer_class"),
        "has_chat_template": bool(template),
        "template_len": len(template),
        "template_mentions_thinking": bool(re.search(r"think|reason|thinking|enable_thinking", template, re.I)),
        "rendered_len": len(rendered),
        "rendered_preview": " ".join(rendered.split())[:1200],
        "render_error": render_error,
    }

    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


if __name__ == "__main__":
    main()

