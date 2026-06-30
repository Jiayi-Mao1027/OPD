from reconcile_opsd.heuristic_eval import evaluate_action_modes, infer_action_mode
from reconcile_opsd.schema import load_jsonl


def test_infer_action_mode_clarification():
    assert infer_action_mode("需要更多上下文，请澄清授权范围。") == "ask_clarification"


def test_infer_action_mode_explicit_label():
    assert infer_action_mode('ACTION_MODE: partial_allowed\nREASON: can answer safe parts') == "partial_allowed"


def test_infer_action_mode_safe_redirect():
    assert infer_action_mode("我不能提供步骤，但可以提供安全替代和防护建议。") == "safe_redirect"


def test_evaluate_action_modes_counts_mismatches():
    examples = load_jsonl("data/reconcilebench_seed.jsonl")
    predictions = {example.id: example.final_response for example in examples}
    result = evaluate_action_modes(examples, predictions)
    assert result.total == len(examples)
    assert 0 <= result.action_mode_accuracy <= 1
    assert result.expected_counts
