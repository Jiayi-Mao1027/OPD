from reconcile_opsd.compact_generation import (
    FIELD_LABELS,
    COMPACT_PROMPT_STYLES,
    COMPACT_TARGET_STYLES,
    OBS_TAG_ORDER,
    compact_target_fields,
    compact_structured_target,
    compact_generation_system_prompt,
    compare_compact_fields,
    expected_compact_fields,
    observable_reason_tag,
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


def test_ontology_prompt_lists_exact_labels_and_schema_rules():
    assert COMPACT_PROMPT_STYLES == ("minimal", "ontology")
    assert COMPACT_TARGET_STYLES == (
        "compact_structured_judgment",
        "compact_winner_delta_tag",
        "compact_winner_obs_tag",
    )
    prompt = compact_generation_system_prompt("ontology")

    assert "GOLD_ACTION: direct_answer | ask_clarification" in prompt
    assert "HARD_AXIS: clarification | fork_state | granularity | refusal_boundary | redirect_boundary | scope_contract" in prompt
    assert "DELTA_TAG: lost_fork_state | missing_clarification" in prompt
    assert "Use HARD_AXIS: scope_contract, not HARD_AXIS: scope." in prompt
    assert "safe_redirect or direct_answer in DELTA_TAG" in prompt
    assert "continue_reasoning" in FIELD_LABELS["GOLD_ACTION"]
    assert "continue_reasoning means a fork-state/internal decision label" in prompt


def test_reduced_winner_delta_target_uses_only_observable_fields():
    record = {
        "winner": "B",
        "gold_action_mode": "safe_redirect",
        "hard_axis": "scope_contract",
        "delta_tag": "wrong_scope",
        "scope_error_direction": "too_broad",
        "gold_judgment": {
            "required_granularity": "redirect_only",
            "fork_policy": "select_with_uncertainty",
        },
    }

    assert compact_target_fields("compact_winner_delta_tag") == ("WINNER", "DELTA_TAG")
    assert expected_compact_fields(record, "compact_winner_delta_tag") == {
        "WINNER": "B",
        "DELTA_TAG": "wrong_scope",
    }
    assert compact_structured_target(record, target_style="compact_winner_delta_tag") == "\n".join(
        [
            "WINNER: B",
            "DELTA_TAG: wrong_scope",
        ]
    )
    assert compact_structured_target(record, winner="A", target_style="compact_winner_delta_tag").splitlines()[0] == "WINNER: A"


def test_reduced_prompt_does_not_request_full_metadata_fields():
    minimal_prompt = compact_generation_system_prompt("minimal", "compact_winner_delta_tag")
    ontology_prompt = compact_generation_system_prompt("ontology", "compact_winner_delta_tag")

    assert "WINNER: <A or B>" in minimal_prompt
    assert "DELTA_TAG: <delta label>" in minimal_prompt
    assert "GOLD_ACTION:" not in minimal_prompt
    assert "HARD_AXIS:" not in minimal_prompt
    assert "WINNER: A | B" in ontology_prompt
    assert "DELTA_TAG: lost_fork_state | missing_clarification" in ontology_prompt
    assert "GOLD_ACTION:" not in ontology_prompt
    assert "continue_reasoning" not in ontology_prompt


def test_observable_reason_tag_uses_winner_action_and_fork_override():
    record = {
        "winner": "B",
        "gold_action_mode": "safe_redirect",
        "primary_action": "safe_redirect",
        "hard_axis": "scope_contract",
        "delta_tag": "wrong_scope",
        "candidate_a": {"action_mode": "direct_answer"},
        "candidate_b": {"action_mode": "safe_redirect"},
    }

    assert observable_reason_tag(record) == "safe_redirect"

    fork_record = {
        **record,
        "gold_action_mode": "partial_allowed",
        "primary_action": "partial_allowed",
        "hard_axis": "fork_state",
        "delta_tag": "lost_fork_state",
        "candidate_b": {"action_mode": "partial_allowed"},
    }

    assert observable_reason_tag(fork_record) == "preserve_fork_state"


def test_observable_reason_tag_uses_gold_action_fallback_and_rejects_bad_actions():
    record = {
        "pair_id": "pair-x",
        "winner": "A",
        "gold_action_mode": "ask_clarification",
        "hard_axis": "clarification",
        "delta_tag": "missing_clarification",
    }

    assert observable_reason_tag(record) == "ask_clarification"

    bad_record = {
        **record,
        "gold_action_mode": "bad_action",
    }
    try:
        observable_reason_tag(bad_record)
    except ValueError as exc:
        assert "cannot derive OBS_TAG for pair-x" in str(exc)
    else:
        raise AssertionError("bad observable action should fail")


def test_winner_obs_tag_target_uses_observable_reason_field():
    record = {
        "winner": "B",
        "gold_action_mode": "safe_redirect",
        "primary_action": "safe_redirect",
        "hard_axis": "scope_contract",
        "delta_tag": "wrong_scope",
        "scope_error_direction": "too_broad",
        "candidate_a": {"action_mode": "direct_answer"},
        "candidate_b": {"action_mode": "safe_redirect"},
        "gold_judgment": {
            "required_granularity": "redirect_only",
            "fork_policy": "select_with_uncertainty",
        },
    }

    assert compact_target_fields("compact_winner_obs_tag") == ("WINNER", "OBS_TAG")
    assert FIELD_LABELS["OBS_TAG"] == OBS_TAG_ORDER
    assert expected_compact_fields(record, "compact_winner_obs_tag") == {
        "WINNER": "B",
        "OBS_TAG": "safe_redirect",
    }
    assert compact_structured_target(record, target_style="compact_winner_obs_tag") == "\n".join(
        [
            "WINNER: B",
            "OBS_TAG: safe_redirect",
        ]
    )
    assert compact_structured_target(record, winner="A", target_style="compact_winner_obs_tag").splitlines()[0] == "WINNER: A"


def test_winner_obs_tag_prompt_and_parser_are_field_scoped():
    minimal_prompt = compact_generation_system_prompt("minimal", "compact_winner_obs_tag")
    ontology_prompt = compact_generation_system_prompt("ontology", "compact_winner_obs_tag")
    parsed = parse_compact_judgment("WINNER: A\nOBS_TAG: preserve_fork_state\n")

    assert "WINNER: <A or B>" in minimal_prompt
    assert "OBS_TAG: <observable reason tag>" in minimal_prompt
    assert "DELTA_TAG:" not in minimal_prompt
    assert "GOLD_ACTION:" not in minimal_prompt
    assert "OBS_TAG: ask_clarification | direct_answer" in ontology_prompt
    assert "DELTA_TAG:" not in ontology_prompt
    assert parsed["OBS_TAG"] == "preserve_fork_state"
    assert parsed_fields_for_output(parsed) == {"winner": "A", "obs_tag": "preserve_fork_state"}


def test_prompt_style_does_not_change_compact_target():
    record = {
        "winner": "A",
        "gold_action_mode": "continue_reasoning",
        "hard_axis": "fork_state",
        "delta_tag": "lost_fork_state",
        "scope_error_direction": "none",
        "gold_judgment": {
            "required_granularity": "bounded_steps",
            "fork_policy": "preserve",
        },
    }

    minimal_prompt = compact_generation_system_prompt("minimal")
    ontology_prompt = compact_generation_system_prompt("ontology")

    assert "continue_reasoning" not in minimal_prompt
    assert "continue_reasoning" in ontology_prompt
    assert compact_structured_target(record) == "\n".join(
        [
            "WINNER: A",
            "GOLD_ACTION: continue_reasoning",
            "HARD_AXIS: fork_state",
            "DELTA_TAG: lost_fork_state",
            "SCOPE_ERROR_DIRECTION: none",
            "REQUIRED_GRANULARITY: bounded_steps",
            "FORK_POLICY: preserve",
        ]
    )


def test_unknown_prompt_style_rejected():
    try:
        compact_generation_system_prompt("bad")
    except ValueError as exc:
        assert "unknown compact generation prompt style" in str(exc)
    else:
        raise AssertionError("bad prompt style should fail")


def test_unknown_compact_target_style_rejected():
    try:
        compact_target_fields("bad")
    except ValueError as exc:
        assert "unknown compact target style" in str(exc)
    else:
        raise AssertionError("bad compact target style should fail")
