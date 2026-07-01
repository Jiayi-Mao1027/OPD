import json
import os
import subprocess
import sys
from pathlib import Path

from reconcile_opsd.candidate_local_data import build_candidate_local_records, candidate_local_manifest, loser_error_tag
from reconcile_opsd.pairwise_data import build_pairwise_records, write_pairwise_jsonl
from reconcile_opsd.schema import load_jsonl


def script_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return env


def test_candidate_local_builder_emits_one_yes_and_one_no_per_pair():
    examples = load_jsonl("data/splits/reconcilebench_v0_1_train.jsonl")
    pair = build_pairwise_records(examples[:1], split_name="train", max_pairs_per_example=1, seed=7, builder_version="pairwise_v0_1")[0]

    records = build_candidate_local_records([pair])

    assert len(records) == 2
    assert {record["candidate_side"] for record in records} == {"A", "B"}
    assert {record["ACCEPTABLE"] for record in records} == {"yes", "no"}
    assert all(record["source_pair_id"] == pair["pair_id"] for record in records)
    assert all(record["source_id"] == pair["source_id"] for record in records)
    assert all(record["prompt_hash"] == pair["prompt_hash"] for record in records)
    assert all(record["hard_axis"] == pair["hard_axis"] for record in records)

    winner = next(record for record in records if record["candidate_side"] == pair["winner"])
    loser = next(record for record in records if record["candidate_side"] != pair["winner"])
    assert winner["ACCEPTABLE"] == "yes"
    assert winner["ERROR_TAG"] == "none"
    assert winner["target"] == "ACCEPTABLE: yes\nERROR_TAG: none"
    assert winner["candidate_is_winner"] is True
    assert loser["ACCEPTABLE"] == "no"
    assert loser["ERROR_TAG"] != "none"
    assert loser["target"].startswith("ACCEPTABLE: no\nERROR_TAG: ")
    assert "ACTION_MODE:" in winner["candidate_text"]
    assert winner["expected_winner_metadata"]["winner"] == pair["winner"]
    assert winner["expected_winner_metadata"]["candidate_a_action"]
    assert winner["expected_winner_metadata"]["candidate_b_action"]


def test_loser_error_tag_uses_conservative_pair_metadata_mapping():
    base = {
        "pair_id": "p1",
        "source_id": "s1",
        "source_split": "dev",
        "prompt": "prompt",
        "candidate_a": {"action_mode": "direct_answer"},
        "candidate_b": {"action_mode": "refuse"},
        "winner": "A",
        "delta_tag": "wrong_scope",
        "hard_axis": "scope_contract",
    }

    unsafe = dict(base, scope_error_direction="unsafe_specificity")
    assert loser_error_tag(unsafe, "B") == ("unsafe_specificity", "scope_error_direction")

    too_narrow = dict(base, scope_error_direction="too_narrow")
    assert loser_error_tag(too_narrow, "B") == ("over_refusal", "scope_error_direction")

    fork = dict(base, delta_tag="lost_fork_state", hard_axis="fork_state", scope_error_direction="none")
    assert loser_error_tag(fork, "B") == ("fork_state", "hard_axis")

    clarification = dict(base, delta_tag="missing_clarification", hard_axis="clarification", scope_error_direction="none")
    assert loser_error_tag(clarification, "B") == ("missing_clarification", "delta_tag")

    unknown = dict(base, delta_tag="wrong_redirect", hard_axis="redirect_boundary", scope_error_direction="none")
    assert loser_error_tag(unknown, "B") == ("over_refusal", "scope_error_direction")


def test_candidate_local_manifest_counts():
    examples = load_jsonl("data/splits/reconcilebench_v0_1_train.jsonl")
    pairs = build_pairwise_records(examples[:2], split_name="train", max_pairs_per_example=1, seed=8, builder_version="pairwise_v0_1")
    records = build_candidate_local_records(pairs)

    manifest = candidate_local_manifest(records, "pairs.jsonl", source_pair_count=len(pairs))

    assert manifest["source_pair_count"] == len(pairs)
    assert manifest["source_pairs_with_examples"] == len(pairs)
    assert manifest["total_examples"] == len(pairs) * 2
    assert manifest["examples_per_pair"] == 2
    assert manifest["candidate_side_counts"] == {"A": len(pairs), "B": len(pairs)}
    assert manifest["acceptable_counts"] == {"no": len(pairs), "yes": len(pairs)}
    assert manifest["error_tag_counts"]["none"] == len(pairs)
    assert manifest["hard_axis_counts"]


def test_candidate_local_cli_writes_jsonl_and_manifest(tmp_path: Path):
    examples = load_jsonl("data/splits/reconcilebench_v0_1_train.jsonl")
    pairs = build_pairwise_records(examples[:2], split_name="train", max_pairs_per_example=1, seed=9, builder_version="pairwise_v0_1")
    source = tmp_path / "pairs.jsonl"
    output = tmp_path / "candidate_local.jsonl"
    manifest = tmp_path / "manifest.json"
    write_pairwise_jsonl(pairs, source)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_candidate_local_data.py",
            "--dataset",
            str(source),
            "--output",
            str(output),
            "--manifest-output",
            str(manifest),
        ],
        env=script_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert len(rows) == len(pairs) * 2
    assert payload["total_examples"] == len(rows)
    assert payload["source_pair_count"] == len(pairs)
    assert payload["acceptable_counts"] == {"no": len(pairs), "yes": len(pairs)}
