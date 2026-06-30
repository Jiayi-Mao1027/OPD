from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCENARIO_TYPES = {
    "clear_harmful",
    "benign_sensitive",
    "dual_use",
    "ambiguous_intent",
    "long_context_distraction",
    "non_safety_uncertainty",
}

ACTION_MODES = {
    "direct_answer",
    "ask_clarification",
    "safe_high_level",
    "safe_redirect",
    "partial_allowed",
    "refuse",
    "continue_reasoning",
}

REQUIRED_FIELDS = {
    "id",
    "prompt",
    "scenario_type",
    "risk_category",
    "benign_allowed_parts",
    "disallowed_parts",
    "initial_judgment",
    "revised_judgment",
    "judgment_delta",
    "action_mode",
    "forks_to_keep",
    "forks_to_prune",
    "final_response",
}


@dataclass(frozen=True)
class ReconcileExample:
    id: str
    prompt: str
    scenario_type: str
    risk_category: str
    benign_allowed_parts: list[str]
    disallowed_parts: list[str]
    initial_judgment: str
    revised_judgment: str
    judgment_delta: str
    action_mode: str
    forks_to_keep: list[str]
    forks_to_prune: list[str]
    final_response: str
    language: str = "zh"
    source: str = "seed"
    tags: list[str] | None = None

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "ReconcileExample":
        validate_record(record)
        allowed = {field.name for field in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        clean = {key: value for key, value in record.items() if key in allowed}
        if "tags" not in clean:
            clean["tags"] = []
        return cls(**clean)


def validate_record(record: dict[str, Any]) -> None:
    missing = sorted(REQUIRED_FIELDS - set(record))
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")

    for field in ["id", "prompt", "scenario_type", "risk_category", "action_mode", "final_response"]:
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")

    if record["scenario_type"] not in SCENARIO_TYPES:
        raise ValueError(f"invalid scenario_type: {record['scenario_type']}")

    if record["action_mode"] not in ACTION_MODES:
        raise ValueError(f"invalid action_mode: {record['action_mode']}")

    for field in ["benign_allowed_parts", "disallowed_parts", "forks_to_keep", "forks_to_prune"]:
        value = record.get(field)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError(f"{field} must be a list of strings")

    for field in ["initial_judgment", "revised_judgment", "judgment_delta"]:
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")


def load_jsonl(path: str | Path) -> list[ReconcileExample]:
    examples: list[ReconcileExample] = []
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                examples.append(ReconcileExample.from_record(record))
            except Exception as exc:
                raise ValueError(f"{path}:{line_no}: {exc}") from exc
    return examples


def dump_jsonl(records: list[dict[str, Any]], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            validate_record(record)
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

