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
