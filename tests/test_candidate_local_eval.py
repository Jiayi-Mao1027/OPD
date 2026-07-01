import json
import os
import subprocess
import sys
from pathlib import Path

from reconcile_opsd.candidate_local_eval import evaluate_candidate_local_scores, load_candidate_local_jsonl


def script_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return env


def candidate_records() -> list[dict[str, object]]:
    return [
        {
            "candidate_id": "p1__A",
            "pair_id": "p1",
            "parent_pair_id": "root1",
            "position_variant": "original",
            "source_id": "s1",
            "source_split": "dev",
            "prompt": "prompt",
            "candidate_side": "A",
            "candidate": {"action_mode": "partial_allowed"},
            "expected_winner": "A",
            "expected_acceptable": "yes",
            "expected_error_tag": "none",
            "pair_delta_tag": "wrong_scope",
            "hard_axis": "scope_contract",
            "scope_error_direction": "unsafe_specificity",
        },
        {
            "candidate_id": "p1__B",
            "pair_id": "p1",
            "parent_pair_id": "root1",
            "position_variant": "original",
            "source_id": "s1",
            "source_split": "dev",
            "prompt": "prompt",
            "candidate_side": "B",
            "candidate": {"action_mode": "direct_answer"},
            "expected_winner": "A",
            "expected_acceptable": "no",
            "expected_error_tag": "wrong_scope",
            "pair_delta_tag": "wrong_scope",
            "hard_axis": "scope_contract",
            "scope_error_direction": "unsafe_specificity",
        },
        {
            "candidate_id": "p1__swapped__A",
            "pair_id": "p1__swapped",
            "parent_pair_id": "root1",
            "position_variant": "swapped",
            "source_id": "s1",
            "source_split": "dev",
            "prompt": "prompt",
            "candidate_side": "A",
            "candidate": {"action_mode": "direct_answer"},
            "expected_winner": "B",
            "expected_acceptable": "no",
            "expected_error_tag": "wrong_scope",
            "pair_delta_tag": "wrong_scope",
            "hard_axis": "scope_contract",
            "scope_error_direction": "unsafe_specificity",
        },
        {
            "candidate_id": "p1__swapped__B",
            "pair_id": "p1__swapped",
            "parent_pair_id": "root1",
            "position_variant": "swapped",
            "source_id": "s1",
            "source_split": "dev",
            "prompt": "prompt",
            "candidate_side": "B",
            "candidate": {"action_mode": "partial_allowed"},
            "expected_winner": "B",
            "expected_acceptable": "yes",
            "expected_error_tag": "none",
            "pair_delta_tag": "wrong_scope",
            "hard_axis": "scope_contract",
            "scope_error_direction": "unsafe_specificity",
        },
    ]


def test_evaluate_candidate_local_scores_induces_pairwise_and_swap():
    records = candidate_records()
    score_rows = {
        "p1__A": {
            "predicted_acceptable": "yes",
            "predicted_error_tag": "none",
            "scores": {"acceptable": {"yes": {"avg_logprob": -0.1}, "no": {"avg_logprob": -1.0}}},
        },
        "p1__B": {
            "predicted_acceptable": "no",
            "predicted_error_tag": "wrong_scope",
            "scores": {"acceptable": {"yes": {"avg_logprob": -1.0}, "no": {"avg_logprob": -0.1}}},
        },
        "p1__swapped__A": {
            "predicted_acceptable": "no",
            "predicted_error_tag": "wrong_scope",
            "scores": {"acceptable": {"yes": {"avg_logprob": -1.0}, "no": {"avg_logprob": -0.1}}},
        },
        "p1__swapped__B": {
            "predicted_acceptable": "yes",
            "predicted_error_tag": "none",
            "scores": {"acceptable": {"yes": {"avg_logprob": -0.1}, "no": {"avg_logprob": -1.0}}},
        },
    }

    result = evaluate_candidate_local_scores(records, score_rows)

    assert result["acceptable_accuracy"] == 1.0
    assert result["error_tag_accuracy"] == 1.0
    assert result["acceptable_macro_f1"] == 1.0
    assert result["induced_pairwise"]["winner_accuracy"] == 1.0
    assert result["induced_pairwise"]["swap_consistency"] == 1.0
    assert result["by_hard_axis"]["scope_contract"]["accuracy"] == 1.0
    assert not result["errors"]


def test_evaluate_candidate_local_scores_records_errors_and_missing():
    records = candidate_records()[:2]
    score_rows = {
        "p1__A": {"predicted_acceptable": "no", "predicted_error_tag": "wrong_scope"},
    }

    result = evaluate_candidate_local_scores(records, score_rows)

    assert result["total"] == 2
    assert result["missing_scores"] == 1
    assert result["acceptable_accuracy"] == 0.0
    assert result["errors"][0]["candidate_id"] == "p1__A"
    assert result["errors"][1]["predicted_acceptable"] == "missing"


def test_load_candidate_local_jsonl_validates_required_fields(tmp_path: Path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"candidate_id":"c1"}\n', encoding="utf-8")

    try:
        load_candidate_local_jsonl(bad)
    except ValueError as exc:
        assert "missing pair_id" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_candidate_local_eval_cli_writes_outputs(tmp_path: Path):
    dataset = tmp_path / "candidate.jsonl"
    scores = tmp_path / "scores.jsonl"
    output_md = tmp_path / "report.md"
    output_json = tmp_path / "report.json"
    output_csv = tmp_path / "errors.csv"
    dataset.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in candidate_records()) + "\n", encoding="utf-8")
    score_rows = [
        {"candidate_id": row["candidate_id"], "predicted_acceptable": row["expected_acceptable"], "predicted_error_tag": row["expected_error_tag"]}
        for row in candidate_records()
    ]
    scores.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in score_rows) + "\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_candidate_local_scores.py",
            "--dataset",
            str(dataset),
            "--scores",
            f"dummy={scores}",
            "--output-md",
            str(output_md),
            "--output-json",
            str(output_json),
            "--output-csv",
            str(output_csv),
        ],
        env=script_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0
    assert "Candidate-Local Reconciliation Eval" in output_md.read_text(encoding="utf-8")
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload[0]["metrics"]["acceptable_accuracy"] == 1.0
    assert output_csv.read_text(encoding="utf-8").startswith("run,candidate_id")
