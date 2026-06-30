from reconcile_opsd.delta_tag_eval import evaluate_delta_tag_scores


def test_evaluate_delta_tag_scores_groups_errors():
    records = [
        {
            "pair_id": "p1",
            "source_id": "s1",
            "delta_tag": "wrong_scope",
            "hard_axis": "scope_contract",
            "winner": "A",
        },
        {
            "pair_id": "p2",
            "source_id": "s2",
            "delta_tag": "lost_fork_state",
            "hard_axis": "fork_state",
            "winner": "B",
        },
        {
            "pair_id": "p3",
            "source_id": "s3",
            "delta_tag": "under_refusal",
            "hard_axis": "refusal_boundary",
            "winner": "A",
        },
    ]
    score_rows = {
        "p1": {"predicted_delta_tag": "wrong_scope", "delta_tag_margin": 0.5},
        "p2": {"predicted_delta_tag": "wrong_scope", "delta_tag_margin": -0.2},
    }

    result = evaluate_delta_tag_scores(records, score_rows)

    assert result["total"] == 3
    assert result["correct"] == 1
    assert result["accuracy"] == 1 / 3
    assert result["missing_scores"] == 1
    assert result["predicted_distribution"] == {"wrong_scope": 2, "missing": 1}
    assert result["by_expected_delta_tag"]["wrong_scope"]["accuracy"] == 1.0
    assert result["by_expected_delta_tag"]["lost_fork_state"]["predictions"] == {"wrong_scope": 1}
    assert result["by_hard_axis"]["scope_contract"]["accuracy"] == 1.0
    assert len(result["errors"]) == 2
