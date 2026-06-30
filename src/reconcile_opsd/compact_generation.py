from __future__ import annotations

import re
from typing import Any


COMPACT_FIELD_ORDER = [
    "WINNER",
    "GOLD_ACTION",
    "HARD_AXIS",
    "DELTA_TAG",
    "SCOPE_ERROR_DIRECTION",
    "REQUIRED_GRANULARITY",
    "FORK_POLICY",
]


FIELD_PATTERN = re.compile(
    r"(?im)^\s*(WINNER|GOLD_ACTION|HARD_AXIS|DELTA_TAG|SCOPE_ERROR_DIRECTION|REQUIRED_GRANULARITY|FORK_POLICY)\s*:\s*(.+?)\s*$"
)


def expected_compact_fields(record: dict[str, Any]) -> dict[str, str]:
    fields = {
        "WINNER": str(record["winner"]),
        "GOLD_ACTION": str(record.get("gold_action_mode", record.get("gold_action", ""))),
        "HARD_AXIS": str(record.get("hard_axis", "other")),
        "DELTA_TAG": str(record["delta_tag"]),
    }
    direction = record.get("scope_error_direction")
    if isinstance(direction, str) and direction:
        fields["SCOPE_ERROR_DIRECTION"] = direction
    judgment = record.get("gold_judgment")
    if isinstance(judgment, dict):
        granularity = judgment.get("required_granularity")
        if isinstance(granularity, str) and granularity:
            fields["REQUIRED_GRANULARITY"] = granularity
        fork_policy = judgment.get("fork_policy")
        if isinstance(fork_policy, str) and fork_policy:
            fields["FORK_POLICY"] = fork_policy
    return {key: fields[key] for key in COMPACT_FIELD_ORDER if key in fields}


def compact_structured_target(record: dict[str, Any], winner: str | None = None) -> str:
    fields = expected_compact_fields(record)
    if winner is not None:
        fields["WINNER"] = winner
    return "\n".join(f"{key}: {fields[key]}" for key in COMPACT_FIELD_ORDER if key in fields)


def parse_compact_judgment(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for match in FIELD_PATTERN.finditer(text):
        key = match.group(1).upper()
        value = clean_field_value(match.group(2))
        if key not in fields:
            fields[key] = value
    return fields


def clean_field_value(value: str) -> str:
    value = value.strip()
    value = value.split("<|", 1)[0].strip()
    value = value.strip("`*_ ")
    return value


def normalize_field_value(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return clean_field_value(value).lower()


def parsed_winner(fields: dict[str, str]) -> str | None:
    winner = fields.get("WINNER", "").strip().upper()
    if winner in {"A", "B"}:
        return winner
    match = re.match(r"^([AB])\s*(?:[).:,-].*)?$", winner)
    if match:
        return match.group(1)
    return None


def compare_compact_fields(expected: dict[str, str], parsed: dict[str, str]) -> dict[str, Any]:
    by_field: dict[str, dict[str, Any]] = {}
    correct = 0
    for key, expected_value in expected.items():
        parsed_value = parsed.get(key)
        is_correct = normalize_field_value(parsed_value) == normalize_field_value(expected_value)
        if is_correct:
            correct += 1
        by_field[key] = {
            "expected": expected_value,
            "parsed": parsed_value,
            "correct": is_correct,
        }
    return {
        "total": len(expected),
        "correct": correct,
        "accuracy": correct / len(expected) if expected else None,
        "by_field": by_field,
    }


def parse_errors_for_compact_judgment(parsed: dict[str, str]) -> list[str]:
    errors: list[str] = []
    if "WINNER" not in parsed:
        errors.append("missing WINNER")
    elif parsed_winner(parsed) is None:
        errors.append(f"invalid WINNER: {parsed.get('WINNER')}")
    return errors


def parsed_fields_for_output(parsed: dict[str, str]) -> dict[str, str]:
    mapping = {
        "WINNER": "winner",
        "GOLD_ACTION": "gold_action",
        "HARD_AXIS": "hard_axis",
        "DELTA_TAG": "delta_tag",
        "SCOPE_ERROR_DIRECTION": "scope_error_direction",
        "REQUIRED_GRANULARITY": "required_granularity",
        "FORK_POLICY": "fork_policy",
    }
    return {mapping[key]: value for key, value in parsed.items() if key in mapping}
