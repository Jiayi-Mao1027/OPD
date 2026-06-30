from reconcile_opsd.compact_generation import (
    compact_structured_target,
    compare_compact_fields,
    expected_compact_fields,
    parse_compact_judgment,
    parse_errors_for_compact_judgment,
    parsed_fields_for_output,
    parsed_winner,
)


def test_parse_compact_judgment_extracts_fields():
    text = """
WINNER: B
GOLD_ACTION: partial_allowed
HARD_AXIS: scope_contract
DELTA_TAG: wrong_scope
SCOPE_ERROR_DIRECTION: unsafe_specificity
"""

    parsed = parse_compact_judgment(text)

    assert parsed["WINNER"] == "B"
    assert parsed["GOLD_ACTION"] == "partial_allowed"
    assert parsed["SCOPE_ERROR_DIRECTION"] == "unsafe_specificity"
    assert parsed_winner(parsed) == "B"


def test_expected_compact_fields_and_comparison():
    record = {
        "winner": "A",
        "gold_action_mode": "safe_redirect",
        "hard_axis": "fork_state",
        "delta_tag": "lost_fork_state",
        "scope_error_direction": "none",
        "gold_judgment": {
            "required_granularity": "high_level",
            "fork_policy": "preserve_until_evidence",
        },
    }
    parsed = {
        "WINNER": "A",
        "GOLD_ACTION": "safe_redirect",
        "HARD_AXIS": "fork_state",
        "DELTA_TAG": "lost_fork_state",
        "SCOPE_ERROR_DIRECTION": "none",
        "REQUIRED_GRANULARITY": "high_level",
        "FORK_POLICY": "wrong_policy",
    }

    expected = expected_compact_fields(record)
    comparison = compare_compact_fields(expected, parsed)

    assert expected["FORK_POLICY"] == "preserve_until_evidence"
    assert comparison["correct"] == 6
    assert comparison["total"] == 7
    assert comparison["by_field"]["FORK_POLICY"]["correct"] is False
    assert compact_structured_target(record).splitlines()[0] == "WINNER: A"
    assert compact_structured_target(record, winner="B").splitlines()[0] == "WINNER: B"


def test_parsed_winner_rejects_missing_or_invalid():
    assert parsed_winner({}) is None
    assert parsed_winner({"WINNER": "C"}) is None
    assert parsed_winner({"WINNER": "A or B"}) is None
    assert parsed_winner({"WINNER": "B - better"}) == "B"


def test_parse_errors_and_output_mapping():
    parsed = parse_compact_judgment("thinking...\n```text\nWINNER: C\nDELTA_TAG: wrong_scope\n```")

    assert parse_errors_for_compact_judgment(parsed) == ["invalid WINNER: C"]
    assert parsed_fields_for_output(parsed) == {"winner": "C", "delta_tag": "wrong_scope"}
    assert parse_errors_for_compact_judgment({}) == ["missing WINNER"]
