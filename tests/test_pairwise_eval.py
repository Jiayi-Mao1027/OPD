import json
import os
import subprocess
import sys
from pathlib import Path

from reconcile_opsd.pairwise_data import build_pairwise_records
from reconcile_opsd.pairwise_eval import evaluate_pairwise_scores, load_pairwise_jsonl, read_pairwise_score_rows
from reconcile_opsd.schema import load_jsonl


def script_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return env


def test_evaluate_pairwise_scores_accuracy_and_margin():
    examples = load_jsonl("data/splits/reconcilebench_v0_train.jsonl")[:2]
    records = build_pairwise_records(examples, split_name="train", max_pairs_per_example=1, seed=4)
    score_rows = {}
    for record in records:
        expected = record["winner"]
        other = "B" if expected == "A" else "A"
        score_rows[record["pair_id"]] = {
            "predicted_winner": expected,
            "scores": {
                expected: {"avg_logprob": -0.1},
                other: {"avg_logprob": -0.9},
            },
        }

    result = evaluate_pairwise_scores(records, score_rows)

    assert result["winner_accuracy"] == 1.0
    assert result["average_winner_margin"] == 0.8
    assert result["missing_scores"] == 0
    assert result["by_expected_side"]
    assert result["score_side_bias"]["count"] == len(records)
    assert "chosen_action_distribution" in result
    assert not result["errors"]


def test_evaluate_pairwise_scores_records_errors():
    examples = load_jsonl("data/splits/reconcilebench_v0_train.jsonl")[:1]
    records = build_pairwise_records(examples, split_name="train", max_pairs_per_example=1, seed=5)
    expected = records[0]["winner"]
    predicted = "B" if expected == "A" else "A"
    score_rows = {
        records[0]["pair_id"]: {
            "predicted_winner": predicted,
            "scores": {
                expected: {"avg_logprob": -1.0},
                predicted: {"avg_logprob": -0.2},
            },
        }
    }

    result = evaluate_pairwise_scores(records, score_rows)

    assert result["winner_accuracy"] == 0.0
    assert result["errors"][0]["pair_id"] == records[0]["pair_id"]
    assert result["errors"][0]["winner_margin"] == -0.8


def test_pairwise_eval_cli_writes_outputs(tmp_path: Path):
    examples = load_jsonl("data/splits/reconcilebench_v0_train.jsonl")[:2]
    records = build_pairwise_records(examples, split_name="train", max_pairs_per_example=1, seed=6)
    dataset = tmp_path / "pairs.jsonl"
    scores = tmp_path / "scores.jsonl"
    output_md = tmp_path / "report.md"
    output_json = tmp_path / "report.json"
    output_csv = tmp_path / "errors.csv"

    with dataset.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    with scores.open("w", encoding="utf-8") as handle:
        for record in records:
            expected = record["winner"]
            other = "B" if expected == "A" else "A"
            handle.write(
                json.dumps(
                    {
                        "pair_id": record["pair_id"],
                        "predicted_winner": expected,
                        "scores": {
                            expected: {"avg_logprob": -0.1},
                            other: {"avg_logprob": -0.9},
                        },
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_pairwise_scores.py",
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
    assert output_md.exists()
    assert output_json.exists()
    assert output_csv.exists()
    assert "winner acc" in output_md.read_text(encoding="utf-8")
    assert "By Hard Axis" in output_md.read_text(encoding="utf-8")


def test_read_pairwise_score_rows(tmp_path: Path):
    path = tmp_path / "scores.jsonl"
    path.write_text('{"pair_id":"p1","predicted_winner":"A"}\n', encoding="utf-8")

    rows = read_pairwise_score_rows(path)

    assert rows["p1"]["predicted_winner"] == "A"


def test_load_pairwise_jsonl_validates_required_fields(tmp_path: Path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"pair_id":"p1"}\n', encoding="utf-8")

    try:
        load_pairwise_jsonl(path)
    except ValueError as exc:
        assert "missing source_id" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_evaluate_pairwise_scores_reports_hard_axis_metrics():
    examples = load_jsonl("data/splits/reconcilebench_v0_train.jsonl")[:2]
    records = build_pairwise_records(examples, split_name="train", max_pairs_per_example=1, seed=9)
    records[0]["hard_axis"] = "fork_state"
    records[0]["scope_error_direction"] = "none"
    score_rows = {}
    for record in records:
        expected = record["winner"]
        other = "B" if expected == "A" else "A"
        score_rows[record["pair_id"]] = {
            "predicted_winner": expected,
            "scores": {
                expected: {"avg_logprob": -0.1},
                other: {"avg_logprob": -0.9},
            },
        }

    result = evaluate_pairwise_scores(records, score_rows)

    assert result["parse_failures"] == 0
    assert result["by_hard_axis"]["fork_state"]["accuracy"] == 1.0
    assert result["fork_preservation_accuracy"] == 1.0
    assert result["by_source_id"]


def test_evaluate_pairwise_scores_reports_position_bias_and_swap_consistency():
    examples = load_jsonl("data/splits/reconcilebench_v0_1_train.jsonl")[:1]
    records = build_pairwise_records(examples, split_name="train", max_pairs_per_example=1, seed=13, builder_version="pairwise_v0_1")
    from reconcile_opsd.pairwise_data import build_position_balanced_records

    balanced = build_position_balanced_records(records)
    score_rows = {}
    for record in balanced:
        score_rows[record["pair_id"]] = {
            "predicted_winner": "A",
            "scores": {
                "A": {"avg_logprob": -0.1},
                "B": {"avg_logprob": -0.5},
            },
        }

    result = evaluate_pairwise_scores(balanced, score_rows)

    assert result["pred_A_rate"] == 1.0
    assert result["pred_B_rate"] == 0.0
    assert result["swap_consistency"] == 0.0
    assert result["swap_diagnostics"]["comparable"] == len(records)
    assert result["swap_diagnostics"]["inconsistent"] == len(records)
    assert result["swap_diagnostics"]["inconsistent_rows"][0]["consistent"] is False
    assert result["side_bias"]["predicted_majority_side"] == "A"
    assert result["side_bias"]["predicted_majority_rate"] == 1.0
    assert result["side_bias"]["min_expected_side_accuracy"] == 0.0
    assert result["position_bias_flag"] is True
    assert result["position_bias_gate"]["status"] == "fail"


def test_swap_failure_analysis_cli_writes_outputs(tmp_path: Path):
    examples = load_jsonl("data/splits/reconcilebench_v0_1_train.jsonl")[:1]
    records = build_pairwise_records(examples, split_name="train", max_pairs_per_example=1, seed=14, builder_version="pairwise_v0_1")
    from reconcile_opsd.pairwise_data import build_position_balanced_records

    balanced = build_position_balanced_records(records)
    score_rows = {
        record["pair_id"]: {
            "predicted_winner": "A",
            "scores": {"A": {"avg_logprob": -0.1}, "B": {"avg_logprob": -0.5}},
        }
        for record in balanced
    }
    metrics = evaluate_pairwise_scores(balanced, score_rows)
    dataset = tmp_path / "balanced.jsonl"
    eval_json = tmp_path / "eval.json"
    output_md = tmp_path / "swap.md"
    output_json = tmp_path / "swap.json"
    output_csv = tmp_path / "swap.csv"
    dataset.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in balanced) + "\n", encoding="utf-8")
    eval_json.write_text(json.dumps([{"name": "dummy", "path": "scores.jsonl", "metrics": metrics}], ensure_ascii=False), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/analyze_pairwise_swap_failures.py",
            "--eval-json",
            str(eval_json),
            "--dataset",
            str(dataset),
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
    assert "Swap-Failure Analysis" in output_md.read_text(encoding="utf-8")
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["runs"][0]["inconsistent"] == 1
    assert output_csv.read_text(encoding="utf-8").startswith("run,parent_pair_id")


def test_evaluate_pairwise_scores_counts_generation_parse_failures():
    examples = load_jsonl("data/splits/reconcilebench_v0_1_train.jsonl")[:1]
    records = build_pairwise_records(examples, split_name="train", max_pairs_per_example=1, seed=17, builder_version="pairwise_v0_1")
    record = records[0]
    score_rows = {
        record["pair_id"]: {
            "pair_id": record["pair_id"],
            "predicted_winner": "invalid",
            "scores": {},
            "score_mode": "compact_structured_generation",
            "field_comparison": {
                "total": 2,
                "correct": 1,
                "by_field": {
                    "WINNER": {"expected": record["winner"], "parsed": None, "correct": False},
                    "DELTA_TAG": {"expected": record["delta_tag"], "parsed": record["delta_tag"], "correct": True},
                },
            },
        }
    }

    result = evaluate_pairwise_scores(records, score_rows)

    assert result["winner_accuracy"] == 0.0
    assert result["parse_failures"] == 1
    assert result["missing_scores"] == 0
    assert result["errors"][0]["pair_id"] == record["pair_id"]
    assert result["score_mode_counts"]["compact_structured_generation"] == 1
    assert result["compact_field_examples"] == 1
    assert result["compact_field_accuracy"] == 0.5
    assert result["compact_field_full_match_rate"] == 0.0
    assert result["by_compact_field"]["DELTA_TAG"]["accuracy"] == 1.0


def test_pairwise_data_audit_cli_writes_outputs(tmp_path: Path):
    examples = load_jsonl("data/splits/reconcilebench_v0_train.jsonl")[:2]
    records = build_pairwise_records(examples, split_name="train", max_pairs_per_example=1, seed=10)
    dataset = tmp_path / "pairs.jsonl"
    output_md = tmp_path / "audit.md"
    output_json = tmp_path / "audit.json"
    output_csv = tmp_path / "audit.csv"

    with dataset.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/audit_pairwise_data.py",
            "--dataset",
            str(dataset),
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
    assert output_md.exists()
    assert output_json.exists()
    assert output_csv.exists()
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["summary"]["total"] == len(records)
