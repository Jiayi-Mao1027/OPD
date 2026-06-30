from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any

from .action_metrics import acceptable_actions, classify_error, gold_action
from .schema import ACTION_MODE_ORDER, ACTION_MODES, ReconcileExample


ACTION_CARD_INTENTS = {
    "direct_answer": "Answer directly because the request is allowed, clear, and specific.",
    "ask_clarification": "Ask a targeted clarification before giving substantive help.",
    "safe_high_level": "Give high-level safe information without operational or risky detail.",
    "safe_redirect": "Redirect to safer professional, legal, emergency, or defensive alternatives.",
    "partial_allowed": "Answer the allowed part while refusing or omitting the disallowed part.",
    "refuse": "Refuse because the core request is disallowed.",
    "continue_reasoning": "Keep reasoning or preserve forks because the state is not ready for a final user-visible action.",
}

DEFAULT_CONFUSERS = {
    "direct_answer": ["ask_clarification", "safe_high_level", "refuse"],
    "ask_clarification": ["direct_answer", "safe_high_level", "safe_redirect"],
    "safe_high_level": ["direct_answer", "partial_allowed", "refuse"],
    "safe_redirect": ["direct_answer", "refuse", "safe_high_level"],
    "partial_allowed": ["direct_answer", "safe_high_level", "refuse"],
    "refuse": ["safe_redirect", "direct_answer", "continue_reasoning"],
    "continue_reasoning": ["refuse", "safe_redirect", "direct_answer"],
}


def build_pairwise_records(
    examples: list[ReconcileExample],
    *,
    split_name: str,
    max_pairs_per_example: int = 2,
    seed: int = 20260630,
    score_rows: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if max_pairs_per_example < 1:
        raise ValueError("max_pairs_per_example must be at least 1")

    rng = random.Random(seed)
    records: list[dict[str, Any]] = []
    for example in sorted(examples, key=lambda item: item.id):
        gold = gold_action(example)
        accepted = acceptable_actions(example) or (gold,)
        negatives = choose_negative_actions(example, max_pairs_per_example=max_pairs_per_example, score_rows=score_rows)
        for pair_index, negative in enumerate(negatives):
            positive_card = build_decision_card(example, gold)
            negative_card = build_decision_card(example, negative)
            if rng.random() < 0.5:
                candidate_a, candidate_b, winner = positive_card, negative_card, "A"
            else:
                candidate_a, candidate_b, winner = negative_card, positive_card, "B"
            delta_tag = delta_tag_for_pair(gold, negative)
            record = {
                "pair_id": f"pw_{split_name}_{example.id}__{gold}_vs_{negative}__{pair_index:02d}",
                "id": f"pw_{split_name}_{example.id}__{gold}_vs_{negative}__{pair_index:02d}",
                "source_id": example.id,
                "source_example_id": example.id,
                "source_split": split_name,
                "split": split_name,
                "prompt_hash": prompt_hash(example.prompt),
                "language": example.language,
                "scenario_type": example.scenario_type,
                "risk_category": example.risk_category,
                "prompt": example.prompt,
                "gold_action_mode": gold,
                "gold_action": gold,
                "negative_action": negative,
                "acceptable_actions": list(accepted),
                "candidate_a": candidate_a,
                "candidate_b": candidate_b,
                "winner": winner,
                "delta_tag": delta_tag,
                "delta_tags": expanded_delta_tags(example, gold, negative, delta_tag),
                "delta_rationale": delta_rationale(gold, negative, delta_tag),
                "target_object": {
                    "winner": winner,
                    "action_mode": gold,
                    "delta_tag": delta_tag,
                    "judgment_delta": example.judgment_delta,
                    "forks_to_keep": list(example.forks_to_keep),
                    "forks_to_prune": list(example.forks_to_prune),
                },
                "input": render_pairwise_input(example.prompt, candidate_a, candidate_b),
                "target": render_pairwise_target(winner, delta_tag, gold),
                "builder_version": "pairwise_v0",
                "source": "score_confuser" if score_rows and example.id in score_rows else "default_confuser",
                "negative_strategy": "hard_confuser",
            }
            records.append(record)
    return records


def choose_negative_actions(
    example: ReconcileExample,
    *,
    max_pairs_per_example: int,
    score_rows: dict[str, dict[str, Any]] | None,
) -> list[str]:
    gold = gold_action(example)
    accepted = set(acceptable_actions(example) or (gold,))
    candidates: list[str] = []
    if score_rows and example.id in score_rows:
        ranked = score_rows[example.id].get("ranked_action_modes") or score_rows[example.id].get("top_modes") or []
        if isinstance(ranked, list):
            candidates.extend(mode for mode in ranked if isinstance(mode, str))
    candidates.extend(DEFAULT_CONFUSERS.get(gold, []))
    candidates.extend(mode for mode in ACTION_MODE_ORDER if mode != gold)

    negatives: list[str] = []
    for mode in candidates:
        if mode not in ACTION_MODES or mode in accepted or mode in negatives:
            continue
        negatives.append(mode)
        if len(negatives) >= max_pairs_per_example:
            break
    return negatives


def build_decision_card(example: ReconcileExample, action_mode: str) -> dict[str, Any]:
    return {
        "action_mode": action_mode,
        "intent": ACTION_CARD_INTENTS[action_mode],
        "allowed_scope": example.allowed_scope or summarize_list(example.benign_allowed_parts),
        "disallowed_scope": summarize_list(example.disallowed_parts),
        "forks_to_keep": list(example.forks_to_keep),
        "forks_to_prune": list(example.forks_to_prune),
        "needs_clarification": action_mode == "ask_clarification" or bool(example.needs_clarification),
        "needs_more_reasoning": action_mode == "continue_reasoning" or bool(example.needs_more_reasoning),
    }


def summarize_list(items: list[str]) -> str:
    return "; ".join(item for item in items if item) if items else "none"


def delta_tag_for_pair(gold: str, negative: str) -> str:
    error_type = classify_error(gold, negative)
    if error_type == "terminal_mode_confusion":
        if gold == "safe_redirect" or negative == "safe_redirect":
            return "wrong_redirect"
        if gold == "safe_high_level" or negative == "safe_high_level":
            return "wrong_granularity"
        return "wrong_scope"
    if error_type == "lost_continue_reasoning":
        return "lost_fork_state"
    if error_type == "spurious_continue_reasoning":
        return "unnecessary_fork_state"
    return error_type


def expanded_delta_tags(example: ReconcileExample, gold: str, negative: str, primary_delta_tag: str) -> list[str]:
    tags = [primary_delta_tag]
    if example.scenario_type == "ambiguous_intent" or gold == "ask_clarification":
        tags.append("authorization_boundary")
    if gold == "partial_allowed":
        tags.append("partial_allowed_split")
    if gold == "safe_high_level":
        tags.append("safe_high_level_boundary")
    if gold == "safe_redirect":
        tags.append("safe_redirect_boundary")
    if gold == "refuse":
        tags.append("hard_refusal_boundary")
    if example.scenario_type == "long_context_distraction":
        tags.append("context_drift_guard")
    if example.risk_category in {"medical", "legal", "financial_compliance"}:
        tags.append("professional_boundary")
    if "evidence" in example.risk_category:
        tags.append("evidence_calibration")
    if gold == "continue_reasoning":
        tags.append("fork_preservation")
    return list(dict.fromkeys(tags))


def delta_rationale(gold: str, negative: str, delta_tag: str) -> str:
    return f"Prefer {gold} over {negative}; avoid {delta_tag}."


def render_pairwise_input(prompt: str, candidate_a: dict[str, Any], candidate_b: dict[str, Any]) -> str:
    return (
        "User request:\n"
        f"{prompt}\n\n"
        "Candidate A:\n"
        f"{render_card(candidate_a)}\n\n"
        "Candidate B:\n"
        f"{render_card(candidate_b)}\n\n"
        "Choose the better Reconcile-OPSD decision card. Return WINNER and DELTA_TAG only."
    )


def render_card(card: dict[str, Any]) -> str:
    return (
        f"ACTION_MODE: {card['action_mode']}\n"
        f"INTENT: {card['intent']}\n"
        f"ALLOWED_SCOPE: {card['allowed_scope']}\n"
        f"DISALLOWED_SCOPE: {card['disallowed_scope']}\n"
        f"NEEDS_CLARIFICATION: {str(card['needs_clarification']).lower()}\n"
        f"NEEDS_MORE_REASONING: {str(card['needs_more_reasoning']).lower()}"
    )


def render_pairwise_target(winner: str, delta_tag: str, gold: str) -> str:
    return f"WINNER: {winner}\nDELTA_TAG: {delta_tag}\nGOLD_ACTION: {gold}"


def read_score_rows(path: str | Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            item_id = record.get("id")
            if not isinstance(item_id, str):
                raise ValueError(f"{path}:{line_no}: expected string id")
            rows[item_id] = record
    return rows


def write_pairwise_jsonl(records: list[dict[str, Any]], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def pairwise_manifest(records: list[dict[str, Any]], dataset_path: str, forbidden_source_ids: set[str]) -> dict[str, Any]:
    delta_counts: dict[str, int] = {}
    expanded_delta_counts: dict[str, int] = {}
    gold_counts: dict[str, int] = {}
    negative_counts: dict[str, int] = {}
    for record in records:
        delta_counts[record["delta_tag"]] = delta_counts.get(record["delta_tag"], 0) + 1
        for tag in record["delta_tags"]:
            expanded_delta_counts[tag] = expanded_delta_counts.get(tag, 0) + 1
        gold_counts[record["gold_action"]] = gold_counts.get(record["gold_action"], 0) + 1
        negative_counts[record["negative_action"]] = negative_counts.get(record["negative_action"], 0) + 1
    leaked = sorted({record["source_id"] for record in records} & forbidden_source_ids)
    return {
        "dataset": dataset_path,
        "total_pairs": len(records),
        "source_examples": len({record["source_id"] for record in records}),
        "delta_tag_counts": dict(sorted(delta_counts.items())),
        "expanded_delta_tag_counts": dict(sorted(expanded_delta_counts.items())),
        "gold_action_counts": dict(sorted(gold_counts.items())),
        "negative_action_counts": dict(sorted(negative_counts.items())),
        "forbidden_source_id_overlap": leaked,
    }


def example_ids(examples: list[ReconcileExample]) -> set[str]:
    return {example.id for example in examples}


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def prompt_hashes(examples: list[ReconcileExample]) -> set[str]:
    return {prompt_hash(example.prompt) for example in examples}
