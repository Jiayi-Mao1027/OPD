import importlib.util
import json
import sys
from pathlib import Path


def load_train_module():
    spec = importlib.util.spec_from_file_location(
        "train_response_lora",
        Path("scripts/train_response_lora.py"),
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class DummyTokenized:
    def __init__(self, input_ids: list[int]):
        self.input_ids = input_ids


class DummyTokenizer:
    eos_token = "<eos>"
    pad_token_id = 0

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True, enable_thinking=False):
        assert tokenize is False
        assert add_generation_prompt is True
        assert enable_thinking is False
        body = "\n".join(f"{message['role']}: {message['content']}" for message in messages)
        return f"{body}\nassistant:"

    def __call__(self, text, add_special_tokens=False):
        assert add_special_tokens is False
        return DummyTokenized([ord(char) % 251 + 1 for char in text])


def test_response_lora_render_uses_prompt_to_final_response_without_label_leakage():
    module = load_train_module()
    source_row = json.loads(Path("data/splits/reconcilebench_v0_1_train.jsonl").read_text(encoding="utf-8").splitlines()[0])
    example = module.ReconcileExample.from_record(source_row)

    prompt, target = module.render_training_example(DummyTokenizer(), example)

    assert example.prompt in prompt
    assert target == f"{example.final_response}<eos>"
    assert example.final_response not in prompt
    for hidden_field in [
        "final_response",
        "revised_judgment",
        "judgment_delta",
        "benign_allowed_parts",
        "disallowed_parts",
        "primary_action",
    ]:
        hidden_value = source_row.get(hidden_field)
        if isinstance(hidden_value, str) and hidden_value.strip():
            assert hidden_value not in prompt
        elif isinstance(hidden_value, list):
            for item in hidden_value:
                assert item not in prompt


def test_response_lora_encoding_masks_prompt_tokens_and_keeps_target_labels():
    module = load_train_module()
    source_row = json.loads(Path("data/splits/reconcilebench_v0_1_train.jsonl").read_text(encoding="utf-8").splitlines()[0])
    example = module.ReconcileExample.from_record(source_row)
    tokenizer = DummyTokenizer()
    prompt, target = module.render_training_example(tokenizer, example)

    encoded = module.encode_example(tokenizer, example, max_length=10_000)

    prompt_len = len(tokenizer(prompt, add_special_tokens=False).input_ids)
    target_len = len(tokenizer(target, add_special_tokens=False).input_ids)
    assert len(encoded.input_ids) == prompt_len + target_len
    assert encoded.labels[:prompt_len] == [-100] * prompt_len
    assert encoded.labels[prompt_len:] == encoded.input_ids[prompt_len:]
    assert any(label != -100 for label in encoded.labels)


def test_response_lora_rejects_unknown_prompt_style():
    module = load_train_module()
    try:
        module.build_messages("hello", prompt_style="boundary_plan")
    except ValueError as exc:
        assert "unknown prompt style" in str(exc)
    else:
        raise AssertionError("expected unknown prompt style to fail")
