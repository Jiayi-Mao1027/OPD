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
