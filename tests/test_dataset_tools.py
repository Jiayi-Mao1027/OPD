from reconcile_opsd.dataset_tools import audit_examples, make_action_mode_split
from reconcile_opsd.schema import load_jsonl


def test_audit_examples_reports_seed_counts():
    examples = load_jsonl("data/reconcilebench_seed.jsonl")
    report = audit_examples(examples)
    assert report["total"] == len(examples)
    assert report["duplicate_ids"] == []
    assert report["action_mode_counts"]
    assert "action_mode_by_scenario_type" in report


def test_make_action_mode_split_covers_every_example_once():
    examples = load_jsonl("data/reconcilebench_seed.jsonl")
    train, dev = make_action_mode_split(examples, dev_ratio=0.25, seed=7)
    train_ids = {example.id for example in train}
    dev_ids = {example.id for example in dev}
    assert train_ids
    assert dev_ids
    assert train_ids.isdisjoint(dev_ids)
    assert train_ids | dev_ids == {example.id for example in examples}
