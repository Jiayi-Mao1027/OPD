from reconcile_opsd.action_metrics import evaluate_action_predictions
from reconcile_opsd.schema import load_jsonl


def test_evaluate_action_predictions_perfect_labels():
    examples = load_jsonl("data/reconcilebench_seed.jsonl")[:5]
    predictions = {example.id: example.action_mode for example in examples}

    result = evaluate_action_predictions(examples, predictions)

    assert result["total"] == len(examples)
    assert result["accuracy"] == 1.0
    assert result["allowed_set_accuracy"] == 1.0
    assert result["hard_boundary_confusions"] == {}


def test_evaluate_action_predictions_score_rows_top2_and_margin():
    examples = load_jsonl("data/reconcilebench_seed.jsonl")[:1]
    example = examples[0]
    score_rows = {
        example.id: {
            "predicted_action_mode": "refuse",
            "ranked_action_modes": ["refuse", example.action_mode],
            "scores": {
                example.action_mode: {"avg_logprob": -1.0},
                "refuse": {"avg_logprob": -0.5},
            },
        }
    }

    result = evaluate_action_predictions(examples, {}, score_rows=score_rows)

    assert result["accuracy"] == 0.0
    assert result["top2_allowed_set_accuracy"] == 1.0
    assert result["average_gold_margin"] == -0.5
    assert result["average_entropy"] is not None


def test_evaluate_action_predictions_can_exclude_continue_reasoning():
    examples = load_jsonl("data/reconcilebench_v0.jsonl")
    predictions = {example.id: example.action_mode for example in examples}

    result = evaluate_action_predictions(examples, predictions, exclude_continue_reasoning=True)

    assert result["excluded_continue_reasoning"] > 0
    assert result["total"] == len(examples) - result["excluded_continue_reasoning"]


def test_confusion_matrix_keeps_predictions_outside_candidate_set():
    examples = load_jsonl("data/reconcilebench_seed.jsonl")[:1]
    gold = examples[0].action_mode
    score_rows = {examples[0].id: {"predicted_action_mode": "continue_reasoning"}}

    result = evaluate_action_predictions(
        examples,
        {},
        score_rows=score_rows,
        candidate_modes=(gold,),
        exclude_continue_reasoning=True,
    )

    assert result["confusion_matrix"][gold]["continue_reasoning"] == 1
