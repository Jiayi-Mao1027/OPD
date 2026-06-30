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

ACTION_MODE_ORDER = [
    "direct_answer",
    "ask_clarification",
    "safe_high_level",
    "safe_redirect",
    "partial_allowed",
    "refuse",
    "continue_reasoning",
]

ACTION_MODES = set(ACTION_MODE_ORDER)

TERMINAL_ACTION_MODES = tuple(mode for mode in ACTION_MODE_ORDER if mode != "continue_reasoning")
VISIBLE_ACTION_MODES = set(TERMINAL_ACTION_MODES)

FORK_RESOLUTIONS = {"resolved", "unresolved", "partially_resolved"}
FORK_POLICIES = {"preserve", "disambiguate", "defer", "select_with_uncertainty"}
COLLAPSE_RISKS = {"none", "over_refusal", "unsafe_answer", "premature_redirect", "premature_answer"}
ANSWERABILITIES = {"full", "partial", "none", "unclear"}
REQUIRED_GRANULARITIES = {"full", "bounded_steps", "high_level", "redirect_only", "refuse_only"}
SCOPE_ERROR_DIRECTIONS = {"none", "too_broad", "too_narrow", "wrong_level", "wrong_object", "unsafe_specificity"}

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
    primary_action: str | None = None
    acceptable_actions: list[str] | None = None
    risk_type: str | None = None
    can_answer: bool | None = None
    missing_critical_info: bool | None = None
    allowed_scope: str | None = None
    needs_clarification: bool | None = None
    needs_uncertainty_expression: bool | None = None
    context_conflict: bool | None = None
    needs_more_reasoning: bool | None = None
    fork_state: dict[str, Any] | None = None
    scope_contract: dict[str, Any] | None = None

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

    primary_action = record.get("primary_action")
    if primary_action is not None:
        if primary_action not in ACTION_MODES:
            raise ValueError(f"invalid primary_action: {primary_action}")
        if primary_action == "continue_reasoning":
            raise ValueError("primary_action must be a user-visible action, not continue_reasoning")

    acceptable_actions = record.get("acceptable_actions")
    if acceptable_actions is not None:
        if not isinstance(acceptable_actions, list) or not all(isinstance(item, str) for item in acceptable_actions):
            raise ValueError("acceptable_actions must be a list of strings")
        invalid_actions = sorted(set(acceptable_actions) - VISIBLE_ACTION_MODES)
        if invalid_actions:
            raise ValueError(f"invalid acceptable_actions: {', '.join(invalid_actions)}")

    for field in ["benign_allowed_parts", "disallowed_parts", "forks_to_keep", "forks_to_prune"]:
        value = record.get(field)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError(f"{field} must be a list of strings")

    for field in ["initial_judgment", "revised_judgment", "judgment_delta"]:
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")

    if record.get("fork_state") is not None:
        validate_fork_state(record["fork_state"])
    if record.get("scope_contract") is not None:
        validate_scope_contract(record["scope_contract"])
    if record.get("needs_more_reasoning") is True:
        fork_state = record.get("fork_state")
        if not isinstance(fork_state, dict) or not fork_state.get("forks_present"):
            raise ValueError("needs_more_reasoning=true requires non-empty fork_state.forks_present")


def validate_fork_state(value: object) -> None:
    if not isinstance(value, dict):
        raise ValueError("fork_state must be an object")
    forks_present = value.get("forks_present", [])
    if not isinstance(forks_present, list) or not all(isinstance(item, str) for item in forks_present):
        raise ValueError("fork_state.forks_present must be a list of strings")
    fork_resolution = value.get("fork_resolution")
    if fork_resolution not in FORK_RESOLUTIONS:
        raise ValueError(f"invalid fork_state.fork_resolution: {fork_resolution}")
    fork_policy = value.get("fork_policy")
    if fork_policy not in FORK_POLICIES:
        raise ValueError(f"invalid fork_state.fork_policy: {fork_policy}")
    collapse_risk = value.get("collapse_risk")
    if collapse_risk not in COLLAPSE_RISKS:
        raise ValueError(f"invalid fork_state.collapse_risk: {collapse_risk}")


def validate_scope_contract(value: object) -> None:
    if not isinstance(value, dict):
        raise ValueError("scope_contract must be an object")
    for field in ["allowed_content", "disallowed_content"]:
        items = value.get(field, [])
        if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
            raise ValueError(f"scope_contract.{field} must be a list of strings")
    answerability = value.get("answerability")
    if answerability not in ANSWERABILITIES:
        raise ValueError(f"invalid scope_contract.answerability: {answerability}")
    required_granularity = value.get("required_granularity")
    if required_granularity not in REQUIRED_GRANULARITIES:
        raise ValueError(f"invalid scope_contract.required_granularity: {required_granularity}")
    scope_error_direction = value.get("scope_error_direction")
    if scope_error_direction not in SCOPE_ERROR_DIRECTIONS:
        raise ValueError(f"invalid scope_contract.scope_error_direction: {scope_error_direction}")


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
