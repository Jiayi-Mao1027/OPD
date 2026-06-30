import csv
import json

from reconcile_opsd.compact_mismatch import (
    load_jsonl,
    parse_run_spec,
    render_markdown,
    summarize_generation_run,
    write_samples_csv,
)


def test_parse_run_spec_splits_name_and_path():
    run = parse_run_spec("base=outputs/base.jsonl")

    assert run.name == "base"
    assert run.path.name == "base.jsonl"


def test_summarize_generation_run_separates_missing_and_schema_confusions():
    row = {
        "pair_id": "pair_001__swapped",
        "source_id": "source_001",
        "expected_winner": "A",
        "predicted_winner": "A",
        "parse_status": "ok",
        "expected_fields": {
            "WINNER": "A",
            "GOLD_ACTION": "safe_high_level",
            "HARD_AXIS": "scope_contract",
            "DELTA_TAG": "wrong_scope",
            "SCOPE_ERROR_DIRECTION": "unsafe_specificity",
            "REQUIRED_GRANULARITY": "high_level",
            "FORK_POLICY": "select_with_uncertainty",
        },
        "parsed_fields": {
            "WINNER": "A",
            "GOLD_ACTION": "safe_high_level",
            "HARD_AXIS": "scope",
            "DELTA_TAG": "GOLD_ACTION",
            "REQUIRED_GRANULARITY": "high_level",
        },
        "raw_generation": "WINNER: A\nGOLD_ACTION: safe_high_level\nHARD_AXIS: scope\nDELTA_TAG: GOLD_ACTION",
    }

    summary = summarize_generation_run("adapter", [row])

    assert summary["winner_accuracy"] == 1.0
    assert summary["full_match_rate"] == 0.0
    assert summary["all_expected_present_rate"] == 0.0
    assert summary["missing_fields"]["SCOPE_ERROR_DIRECTION"] == 1
    assert summary["missing_fields"]["FORK_POLICY"] == 1
    assert summary["field_stats"]["HARD_AXIS"]["accuracy"] == 0.0
    assert summary["field_stats"]["REQUIRED_GRANULARITY"]["accuracy"] == 1.0
    assert summary["by_hard_axis"]["scope_contract"]["winner_accuracy"] == 1.0
    assert ("HARD_AXIS", "scope", "possible_truncation_or_alias") in summary["confusions"]
    assert ("DELTA_TAG", "GOLD_ACTION", "value_is_field_name:GOLD_ACTION") in summary["confusions"]
    assert summary["samples"][0]["is_swapped"] is True


def test_load_render_and_write_samples(tmp_path):
    input_path = tmp_path / "gen.jsonl"
    row = {
        "pair_id": "pair_001",
        "expected_winner": "B",
        "predicted_winner": "invalid",
        "parse_status": "failed",
        "expected_fields": {"WINNER": "B", "DELTA_TAG": "wrong_scope"},
        "parsed_fields": {"DELTA_TAG": "wrong_scope"},
        "raw_generation": "DELTA_TAG: wrong_scope",
    }
    input_path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    loaded = load_jsonl(input_path)
    summary = summarize_generation_run("base", loaded)
    markdown = render_markdown([summary], max_samples_per_run=1)
    csv_path = tmp_path / "samples.csv"
    write_samples_csv(csv_path, [summary], max_samples_per_run=1)

    assert summary["parse_failure_rate"] == 1.0
    assert "Pairwise v0.1 Compact Generation Mismatch Analysis" in markdown
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["run"] == "base"
    assert rows[0]["missing_fields"] == "WINNER"
