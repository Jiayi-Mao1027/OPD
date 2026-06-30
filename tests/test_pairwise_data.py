import json
import os
import subprocess
import sys
from pathlib import Path

from reconcile_opsd.pairwise_data import build_pairwise_records, build_position_balanced_records, pairwise_manifest, prompt_hashes
from reconcile_opsd.schema import ACTION_MODES, load_jsonl


def script_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return env


def test_pairwise_builder_required_fields_and_winner():
    examples = load_jsonl("data/splits/reconcilebench_v0_train.jsonl")
    records = build_pairwise_records(examples[:3], split_name="train", max_pairs_per_example=2, seed=1)

    assert records
    for record in records:
        assert record["pair_id"]
        assert record["source_id"]
        assert record["source_split"] == "train"
        assert record["prompt_hash"]
        assert record["winner"] in {"A", "B"}
        winner_card = record["candidate_a"] if record["winner"] == "A" else record["candidate_b"]
        loser_card = record["candidate_b"] if record["winner"] == "A" else record["candidate_a"]
        assert winner_card["action_mode"] == record["gold_action_mode"]
        assert loser_card["action_mode"] != winner_card["action_mode"]
        assert record["delta_tag"]
        assert record["target_object"]["action_mode"] == record["gold_action_mode"]
        assert "WINNER:" in record["target"]


def test_pairwise_builder_no_dev_leak():
    train = load_jsonl("data/splits/reconcilebench_v0_train.jsonl")
    dev = load_jsonl("data/splits/reconcilebench_v0_dev.jsonl")
    records = build_pairwise_records(train, split_name="train", max_pairs_per_example=1, seed=2)

    dev_ids = {example.id for example in dev}
    dev_hashes = prompt_hashes(dev)
    assert {record["source_id"] for record in records}.isdisjoint(dev_ids)
    assert {record["prompt_hash"] for record in records}.isdisjoint(dev_hashes)


def test_pairwise_builder_covers_action_modes_and_delta_tags():
    examples = load_jsonl("data/splits/reconcilebench_v0_train.jsonl")
    records = build_pairwise_records(examples, split_name="train", max_pairs_per_example=2, seed=3)

    assert {record["gold_action_mode"] for record in records} == ACTION_MODES
    delta_tags = {tag for record in records for tag in record["delta_tags"]}
    assert "missing_clarification" in delta_tags
    assert "partial_allowed_split" in delta_tags
    assert "safe_redirect_boundary" in delta_tags
    assert "hard_refusal_boundary" in delta_tags
    assert "context_drift_guard" in delta_tags
    assert "fork_preservation" in delta_tags


def test_pairwise_position_randomization_is_not_constant():
    examples = load_jsonl("data/splits/reconcilebench_v0_train.jsonl")
    records = build_pairwise_records(examples, split_name="train", max_pairs_per_example=2, seed=20260630)
    winners = [record["winner"] for record in records]

    assert "A" in winners
    assert "B" in winners


def test_pairwise_cli_rejects_forbidden_source_dataset(tmp_path: Path):
    output = tmp_path / "pairs.jsonl"
    manifest = tmp_path / "manifest.json"
    command = [
        sys.executable,
        "scripts/build_pairwise_judgment_data.py",
        "--dataset",
        "data/splits/reconcilebench_v0_train.jsonl",
        "--forbid-source-dataset",
        "data/splits/reconcilebench_v0_train.jsonl",
        "--output",
        str(output),
        "--manifest-output",
        str(manifest),
    ]

    result = subprocess.run(command, env=script_env(), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    assert result.returncode != 0
    assert "forbidden source ids" in result.stderr


def test_pairwise_cli_writes_manifest(tmp_path: Path):
    output = tmp_path / "pairs.jsonl"
    manifest = tmp_path / "manifest.json"
    command = [
        sys.executable,
        "scripts/build_pairwise_judgment_data.py",
        "--dataset",
        "data/splits/reconcilebench_v0_train.jsonl",
        "--forbid-source-dataset",
        "data/splits/reconcilebench_v0_dev.jsonl",
        "--output",
        str(output),
        "--manifest-output",
        str(manifest),
        "--max-pairs-per-example",
        "1",
    ]

    result = subprocess.run(command, env=script_env(), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    assert result.returncode == 0
    assert output.exists()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["forbidden_source_id_overlap"] == []
    assert payload["forbidden_prompt_hash_overlap"] == []
    assert payload["total_pairs"] == len(output.read_text(encoding="utf-8").splitlines())


def test_pairwise_v0_1_records_include_hard_axis_and_gold_judgment(tmp_path: Path):
    enriched = tmp_path / "train_v0_1.jsonl"
    enrich_result = subprocess.run(
        [
            sys.executable,
            "scripts/enrich_reconcilebench_v0_1.py",
            "--dataset",
            "data/splits/reconcilebench_v0_train.jsonl",
            "--output",
            str(enriched),
        ],
        env=script_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert enrich_result.returncode == 0
    examples = load_jsonl(enriched)
    records = build_pairwise_records(examples, split_name="train", max_pairs_per_example=2, seed=7, builder_version="pairwise_v0_1")

    assert records
    assert "lost_fork_state" in {record["delta_tag"] for record in records}
    assert "wrong_scope" in {record["delta_tag"] for record in records}
    for record in records:
        assert record["builder_version"] == "pairwise_v0_1"
        assert record["hard_axis"]
        assert record["gold_judgment"]["primary_action"] != "continue_reasoning"
        assert record["candidate_a"]["decision_card"]["primary_action"] != "continue_reasoning"
        assert record["candidate_b"]["decision_card"]["primary_action"] != "continue_reasoning"
        assert record["candidate_a"]["response_sketch"]
        assert record["candidate_b"]["response_sketch"]
    lost_fork = [record for record in records if record["delta_tag"] == "lost_fork_state"]
    assert lost_fork
    for record in lost_fork:
        assert record["hard_axis"] == "fork_state"
    wrong_scope = [record for record in records if record["delta_tag"] == "wrong_scope"]
    assert wrong_scope
    assert all(record["scope_error_direction"] != "none" for record in wrong_scope)


def test_pairwise_card_rendering_keeps_decision_fields_on_separate_lines():
    examples = load_jsonl("data/splits/reconcilebench_v0_1_train.jsonl")
    records = build_pairwise_records(examples[:1], split_name="train", max_pairs_per_example=1, seed=7, builder_version="pairwise_v0_1")

    rendered = records[0]["input"]

    assert "\nFORK_POLICY: " in rendered
    assert "\nSCOPE_ANSWERABILITY: " in rendered
    assert "\nREQUIRED_GRANULARITY: " in rendered
    assert "SCOPE_ANSWERABILITY:" not in rendered.split("FORK_POLICY:", maxsplit=1)[1].splitlines()[0]


def test_pairwise_v0_1_manifest_counts(tmp_path: Path):
    enriched = tmp_path / "train_v0_1.jsonl"
    subprocess.run(
        [
            sys.executable,
            "scripts/enrich_reconcilebench_v0_1.py",
            "--dataset",
            "data/splits/reconcilebench_v0_train.jsonl",
            "--output",
            str(enriched),
        ],
        env=script_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    records = build_pairwise_records(load_jsonl(enriched), split_name="train", max_pairs_per_example=1, seed=8, builder_version="pairwise_v0_1")
    manifest = pairwise_manifest(records, str(enriched), set())

    assert manifest["builder_versions"] == ["pairwise_v0_1"]
    assert manifest["hard_axis_counts"]
    assert manifest["scope_error_direction_counts"]
    assert manifest["winner_counts"]


def test_position_balanced_records_swap_candidates_and_targets():
    examples = load_jsonl("data/splits/reconcilebench_v0_1_train.jsonl")[:1]
    records = build_pairwise_records(examples, split_name="train", max_pairs_per_example=1, seed=11, builder_version="pairwise_v0_1")

    balanced = build_position_balanced_records(records)

    assert len(balanced) == 2
    original, swapped = balanced
    assert original["position_variant"] == "original"
    assert swapped["position_variant"] == "swapped"
    assert swapped["parent_pair_id"] == original["pair_id"]
    assert swapped["pair_id"] == f"{original['pair_id']}__swapped"
    assert swapped["winner"] != original["winner"]
    assert swapped["candidate_a"] == original["candidate_b"]
    assert swapped["candidate_b"] == original["candidate_a"]
    assert swapped["gold_judgment"]["winner"] == swapped["winner"]
    assert swapped["target_object"]["winner"] == swapped["winner"]
    assert f"WINNER: {swapped['winner']}" in swapped["target"]


def test_position_balanced_cli_writes_manifest(tmp_path: Path):
    examples = load_jsonl("data/splits/reconcilebench_v0_1_train.jsonl")[:2]
    records = build_pairwise_records(examples, split_name="train", max_pairs_per_example=1, seed=12, builder_version="pairwise_v0_1")
    source = tmp_path / "pairs.jsonl"
    output = tmp_path / "balanced.jsonl"
    manifest = tmp_path / "manifest.json"
    source.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_position_balanced_pairwise.py",
            "--input",
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

    assert result.returncode == 0
    assert len(output.read_text(encoding="utf-8").splitlines()) == len(records) * 2
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["position_variant_counts"] == {"original": len(records), "swapped": len(records)}
