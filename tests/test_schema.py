import json
from pathlib import Path

import pytest

from reconcile_opsd.schema import load_jsonl, validate_record


def test_seed_dataset_loads():
    examples = load_jsonl(Path("data/reconcilebench_seed.jsonl"))
    assert len(examples) >= 10
    assert {example.action_mode for example in examples}


def test_validate_record_rejects_missing_fields():
    with pytest.raises(ValueError, match="missing required fields"):
        validate_record({"id": "bad"})


def test_validate_record_rejects_invalid_action_mode():
    record = json.loads(Path("data/reconcilebench_seed.jsonl").read_text(encoding="utf-8").splitlines()[0])
    record["action_mode"] = "unsafe_mode"
    with pytest.raises(ValueError, match="invalid action_mode"):
        validate_record(record)


def test_validate_record_accepts_optional_decision_axes():
    record = json.loads(Path("data/reconcilebench_seed.jsonl").read_text(encoding="utf-8").splitlines()[0])
    record["primary_action"] = record["action_mode"]
    record["acceptable_actions"] = [record["action_mode"], "ask_clarification"]
    record["risk_type"] = "over_refusal"
    record["can_answer"] = True
    record["missing_critical_info"] = False
    validate_record(record)


def test_validate_record_rejects_invalid_acceptable_actions():
    record = json.loads(Path("data/reconcilebench_seed.jsonl").read_text(encoding="utf-8").splitlines()[0])
    record["acceptable_actions"] = ["not_a_mode"]
    with pytest.raises(ValueError, match="invalid acceptable_actions"):
        validate_record(record)


def test_validate_record_accepts_v0_1_fork_and_scope_fields():
    record = json.loads(Path("data/reconcilebench_seed.jsonl").read_text(encoding="utf-8").splitlines()[0])
    record["primary_action"] = "safe_high_level"
    record["acceptable_actions"] = ["safe_high_level", "partial_allowed"]
    record["needs_more_reasoning"] = True
    record["fork_state"] = {
        "forks_present": ["allowed high-level help", "unsafe operational detail"],
        "fork_resolution": "unresolved",
        "fork_policy": "preserve",
        "collapse_risk": "premature_answer",
    }
    record["scope_contract"] = {
        "answerability": "partial",
        "allowed_content": ["high-level safety context"],
        "disallowed_content": ["operational harmful detail"],
        "required_granularity": "high_level",
        "scope_error_direction": "none",
    }

    validate_record(record)


def test_validate_record_rejects_continue_reasoning_primary_action():
    record = json.loads(Path("data/reconcilebench_seed.jsonl").read_text(encoding="utf-8").splitlines()[0])
    record["primary_action"] = "continue_reasoning"

    with pytest.raises(ValueError, match="primary_action must be a user-visible action"):
        validate_record(record)


def test_validate_record_rejects_needs_more_reasoning_without_forks():
    record = json.loads(Path("data/reconcilebench_seed.jsonl").read_text(encoding="utf-8").splitlines()[0])
    record["needs_more_reasoning"] = True
    record["fork_state"] = {
        "forks_present": [],
        "fork_resolution": "unresolved",
        "fork_policy": "preserve",
        "collapse_risk": "premature_answer",
    }

    with pytest.raises(ValueError, match="requires non-empty fork_state"):
        validate_record(record)


def test_validate_record_rejects_invalid_scope_contract_value():
    record = json.loads(Path("data/reconcilebench_seed.jsonl").read_text(encoding="utf-8").splitlines()[0])
    record["scope_contract"] = {
        "answerability": "partial",
        "allowed_content": [],
        "disallowed_content": [],
        "required_granularity": "bad_granularity",
        "scope_error_direction": "none",
    }

    with pytest.raises(ValueError, match="invalid scope_contract.required_granularity"):
        validate_record(record)
