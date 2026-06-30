from __future__ import annotations

import copy
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

BUILDER_VERSIONS = {"pairwise_v0", "pairwise_v0_1"}

HARD_AXIS_BY_DELTA = {
    "lost_fork_state": "fork_state",
    "unnecessary_fork_state": "fork_state",
    "wrong_scope": "scope_contract",
    "wrong_granularity": "granularity",
    "missing_clarification": "clarification",
    "unnecessary_clarification": "clarification",
    "under_refusal": "refusal_boundary",
    "over_refusal": "refusal_boundary",
    "wrong_redirect": "redirect_boundary",
}


def build_pairwise_records(
    examples: list[ReconcileExample],
    *,
    split_name: str,
    max_pairs_per_example: int = 2,
    seed: int = 20260630,
    score_rows: dict[str, dict[str, Any]] | None = None,
    builder_version: str = "pairwise_v0",
) -> list[dict[str, Any]]:
    if max_pairs_per_example < 1:
        raise ValueError("max_pairs_per_example must be at least 1")
    if builder_version not in BUILDER_VERSIONS:
        raise ValueError(f"invalid builder_version: {builder_version}")

    rng = random.Random(seed)
    records: list[dict[str, Any]] = []
    for example in sorted(examples, key=lambda item: item.id):
        gold = visible_gold_action(example, builder_version)
        accepted = acceptable_actions(example) or (gold,)
        negatives = choose_negative_actions(
            example,
            max_pairs_per_example=max_pairs_per_example,
            score_rows=score_rows,
            builder_version=builder_version,
            gold=gold,
        )
        for pair_index, negative in enumerate(negatives):
            positive_card = build_decision_card(example, gold, builder_version=builder_version, is_gold=True)
            negative_card = build_decision_card(example, negative, builder_version=builder_version, is_gold=False)
            if rng.random() < 0.5:
                candidate_a, candidate_b, winner = positive_card, negative_card, "A"
            else:
                candidate_a, candidate_b, winner = negative_card, positive_card, "B"
            delta_tag = delta_tag_for_pair(example, gold, negative, builder_version=builder_version)
            hard_axis = hard_axis_for_pair(delta_tag)
            scope_error_direction = scope_error_direction_for_pair(example, gold, negative, delta_tag)
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
                "primary_action": gold,
                "negative_action": negative,
                "acceptable_actions": list(accepted),
                "candidate_a": candidate_a,
                "candidate_b": candidate_b,
                "winner": winner,
                "delta_tag": delta_tag,
                "delta_tags": expanded_delta_tags(example, gold, negative, delta_tag),
                "delta_rationale": delta_rationale(gold, negative, delta_tag),
                "hard_axis": hard_axis,
                "scope_error_direction": scope_error_direction,
                "target_object": {
                    "winner": winner,
                    "action_mode": gold,
                    "delta_tag": delta_tag,
                    "hard_axis": hard_axis,
                    "scope_error_direction": scope_error_direction,
                    "judgment_delta": example.judgment_delta,
                    "forks_to_keep": list(example.forks_to_keep),
                    "forks_to_prune": list(example.forks_to_prune),
                    "fork_state": example.fork_state,
                    "scope_contract": example.scope_contract,
                },
                "gold_judgment": {
                    "winner": winner,
                    "delta_tag": delta_tag,
                    "primary_action": gold,
                    "needs_more_reasoning": bool(example.needs_more_reasoning),
                    "fork_policy": fork_policy(example),
                    "scope_error_direction": scope_error_direction,
                    "required_granularity": required_granularity(example),
                },
                "input": render_pairwise_input(example.prompt, candidate_a, candidate_b),
                "target": render_pairwise_target(
                    winner,
                    delta_tag,
                    gold,
                    hard_axis=hard_axis if builder_version == "pairwise_v0_1" else None,
                    scope_error_direction=scope_error_direction if builder_version == "pairwise_v0_1" else None,
                    required_granularity=required_granularity(example) if builder_version == "pairwise_v0_1" else None,
                ),
                "builder_version": builder_version,
                "source": "score_confuser" if score_rows and example.id in score_rows else "default_confuser",
                "negative_strategy": "hard_confuser",
            }
            records.append(record)
    return records


def visible_gold_action(example: ReconcileExample, builder_version: str) -> str:
    gold = gold_action(example)
    if builder_version == "pairwise_v0_1" and gold == "continue_reasoning":
        if example.primary_action and example.primary_action != "continue_reasoning":
            return example.primary_action
        if example.disallowed_parts:
            return "partial_allowed"
        return "safe_high_level"
    return gold


def choose_negative_actions(
    example: ReconcileExample,
    *,
    max_pairs_per_example: int,
    score_rows: dict[str, dict[str, Any]] | None,
    builder_version: str = "pairwise_v0",
    gold: str | None = None,
) -> list[str]:
    gold = gold or visible_gold_action(example, builder_version)
    accepted = set(acceptable_actions(example) or (gold,))
    candidates: list[str] = []
    if builder_version == "pairwise_v0_1":
        candidates.extend(v0_1_priority_negatives(example, gold))
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


def v0_1_priority_negatives(example: ReconcileExample, gold: str) -> list[str]:
    candidates: list[str] = []
    if example.needs_more_reasoning:
        candidates.extend(["direct_answer", "refuse", "safe_redirect"])
    if gold == "partial_allowed" or scope_answerability(example) == "partial":
        candidates.extend(["direct_answer", "refuse", "safe_redirect", "safe_high_level"])
    if gold == "ask_clarification":
        candidates.extend(["direct_answer", "safe_high_level"])
    return candidates


def build_decision_card(
    example: ReconcileExample,
    action_mode: str,
    *,
    builder_version: str = "pairwise_v0",
    is_gold: bool = False,
) -> dict[str, Any]:
    card = {
        "action_mode": action_mode,
        "intent": ACTION_CARD_INTENTS[action_mode],
        "allowed_scope": example.allowed_scope or summarize_list(example.benign_allowed_parts),
        "disallowed_scope": summarize_list(example.disallowed_parts),
        "forks_to_keep": list(example.forks_to_keep),
        "forks_to_prune": list(example.forks_to_prune),
        "needs_clarification": action_mode == "ask_clarification" or bool(example.needs_clarification),
        "needs_more_reasoning": action_mode == "continue_reasoning" or bool(example.needs_more_reasoning),
    }
    if builder_version == "pairwise_v0_1":
        decision_card = {
            "primary_action": action_mode,
            "acceptable_actions": list(example.acceptable_actions or [action_mode]),
            "risk_type": example.risk_type or example.risk_category,
            "can_answer": action_mode in {"direct_answer", "safe_high_level", "safe_redirect", "partial_allowed"},
            "fork_state": candidate_fork_state(example, is_gold=is_gold),
            "scope_contract": candidate_scope_contract(example, action_mode, is_gold=is_gold),
        }
        card.update(
            {
                "decision_card": decision_card,
                "response_sketch": response_sketch(action_mode),
            }
        )
    return card


def summarize_list(items: list[str]) -> str:
    return "; ".join(item for item in items if item) if items else "none"


def delta_tag_for_pair(
    example: ReconcileExample,
    gold: str,
    negative: str,
    *,
    builder_version: str = "pairwise_v0",
) -> str:
    if builder_version == "pairwise_v0_1":
        if example.needs_more_reasoning and negative in {"direct_answer", "refuse", "safe_redirect"}:
            return "lost_fork_state"
        if gold == "partial_allowed" or scope_answerability(example) == "partial":
            if negative in {"direct_answer", "refuse", "safe_redirect", "safe_high_level"}:
                return "wrong_scope"
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


def hard_axis_for_pair(delta_tag: str) -> str:
    return HARD_AXIS_BY_DELTA.get(delta_tag, "other")


def scope_error_direction_for_pair(example: ReconcileExample, gold: str, negative: str, delta_tag: str) -> str:
    if delta_tag != "wrong_scope":
        return "none"
    if negative == "direct_answer":
        if example.disallowed_parts:
            return "unsafe_specificity"
        return "too_broad"
    if negative == "refuse":
        return "too_narrow"
    if negative == "safe_redirect":
        return "wrong_level"
    if negative == "safe_high_level" and gold == "partial_allowed":
        return "too_narrow"
    return "wrong_object"


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
    lines = [
        f"ACTION_MODE: {card['action_mode']}",
        f"INTENT: {card['intent']}",
        f"ALLOWED_SCOPE: {card['allowed_scope']}",
        f"DISALLOWED_SCOPE: {card['disallowed_scope']}",
        f"NEEDS_CLARIFICATION: {str(card['needs_clarification']).lower()}",
        f"NEEDS_MORE_REASONING: {str(card['needs_more_reasoning']).lower()}",
    ]
    decision_card = card.get("decision_card")
    if isinstance(decision_card, dict):
        fork_state = decision_card.get("fork_state") if isinstance(decision_card.get("fork_state"), dict) else {}
        scope_contract = decision_card.get("scope_contract") if isinstance(decision_card.get("scope_contract"), dict) else {}
        lines.extend(
            [
                f"FORK_POLICY: {fork_state.get('fork_policy', 'none')}",
                f"SCOPE_ANSWERABILITY: {scope_contract.get('answerability', 'unclear')}",
                f"REQUIRED_GRANULARITY: {scope_contract.get('required_granularity', 'high_level')}",
                f"RESPONSE_SKETCH: {card.get('response_sketch', '')}",
            ]
        )
    return "\n".join(lines)


def render_pairwise_target(
    winner: str,
    delta_tag: str,
    gold: str,
    *,
    hard_axis: str | None = None,
    scope_error_direction: str | None = None,
    required_granularity: str | None = None,
) -> str:
    lines = [f"WINNER: {winner}", f"DELTA_TAG: {delta_tag}", f"GOLD_ACTION: {gold}"]
    if hard_axis:
        lines.append(f"HARD_AXIS: {hard_axis}")
    if scope_error_direction:
        lines.append(f"SCOPE_ERROR_DIRECTION: {scope_error_direction}")
    if required_granularity:
        lines.append(f"REQUIRED_GRANULARITY: {required_granularity}")
    return "\n".join(lines)


def candidate_fork_state(example: ReconcileExample, *, is_gold: bool) -> dict[str, Any]:
    source = example.fork_state or {
        "forks_present": list(example.forks_to_keep),
        "fork_resolution": "unresolved" if example.needs_more_reasoning else "resolved",
        "fork_policy": "preserve" if example.needs_more_reasoning else "select_with_uncertainty",
        "collapse_risk": "none",
    }
    fork_state = dict(source)
    if example.needs_more_reasoning and not is_gold:
        fork_state["fork_resolution"] = "resolved"
        fork_state["fork_policy"] = "select_with_uncertainty"
        fork_state["collapse_risk"] = fork_state.get("collapse_risk") or "premature_answer"
    return fork_state


def candidate_scope_contract(example: ReconcileExample, action_mode: str, *, is_gold: bool) -> dict[str, Any]:
    source = example.scope_contract or {
        "answerability": scope_answerability(example),
        "allowed_content": list(example.benign_allowed_parts),
        "disallowed_content": list(example.disallowed_parts),
        "required_granularity": required_granularity(example),
        "scope_error_direction": "none",
    }
    contract = dict(source)
    contract["answerability"] = answerability_for_action(action_mode)
    contract["required_granularity"] = granularity_for_action(action_mode)
    contract["scope_error_direction"] = "none" if is_gold else scope_error_direction_for_pair(example, "", action_mode, "wrong_scope")
    return contract


def response_sketch(action_mode: str) -> str:
    return ACTION_CARD_INTENTS[action_mode]


def scope_answerability(example: ReconcileExample) -> str:
    contract = example.scope_contract or {}
    answerability = contract.get("answerability")
    return answerability if isinstance(answerability, str) else answerability_for_action(gold_action(example))


def required_granularity(example: ReconcileExample) -> str:
    contract = example.scope_contract or {}
    granularity = contract.get("required_granularity")
    return granularity if isinstance(granularity, str) else granularity_for_action(gold_action(example))


def fork_policy(example: ReconcileExample) -> str:
    fork_state = example.fork_state or {}
    policy = fork_state.get("fork_policy")
    return policy if isinstance(policy, str) else ("preserve" if example.needs_more_reasoning else "select_with_uncertainty")


def answerability_for_action(action_mode: str) -> str:
    return {
        "direct_answer": "full",
        "ask_clarification": "unclear",
        "safe_high_level": "partial",
        "safe_redirect": "partial",
        "partial_allowed": "partial",
        "refuse": "none",
        "continue_reasoning": "unclear",
    }.get(action_mode, "unclear")


def granularity_for_action(action_mode: str) -> str:
    return {
        "direct_answer": "full",
        "ask_clarification": "high_level",
        "safe_high_level": "high_level",
        "safe_redirect": "redirect_only",
        "partial_allowed": "bounded_steps",
        "refuse": "refuse_only",
        "continue_reasoning": "high_level",
    }.get(action_mode, "high_level")


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


def build_position_balanced_records(
    records: list[dict[str, Any]],
    *,
    include_original: bool = True,
    include_swapped: bool = True,
) -> list[dict[str, Any]]:
    if not include_original and not include_swapped:
        raise ValueError("At least one of include_original/include_swapped must be true")

    balanced: list[dict[str, Any]] = []
    for record in records:
        if include_original:
            original = copy.deepcopy(record)
            original["parent_pair_id"] = record.get("parent_pair_id", record["pair_id"])
            original["position_variant"] = "original"
            original["gold_position"] = record["winner"]
            balanced.append(original)
        if include_swapped:
            balanced.append(swapped_pairwise_record(record))
    return balanced


def swapped_pairwise_record(record: dict[str, Any]) -> dict[str, Any]:
    swapped = copy.deepcopy(record)
    original_pair_id = record["pair_id"]
    flipped = flip_winner(record["winner"])
    swapped["pair_id"] = f"{original_pair_id}__swapped"
    swapped["id"] = swapped["pair_id"]
    swapped["parent_pair_id"] = record.get("parent_pair_id", original_pair_id)
    swapped["position_variant"] = "swapped"
    swapped["gold_position"] = flipped
    swapped["candidate_a"] = copy.deepcopy(record["candidate_b"])
    swapped["candidate_b"] = copy.deepcopy(record["candidate_a"])
    swapped["winner"] = flipped
    target_object = swapped.get("target_object")
    if isinstance(target_object, dict):
        target_object["winner"] = flipped
    gold_judgment = swapped.get("gold_judgment")
    if isinstance(gold_judgment, dict):
        gold_judgment["winner"] = flipped
    swapped["input"] = render_pairwise_input(swapped["prompt"], swapped["candidate_a"], swapped["candidate_b"])
    swapped["target"] = render_pairwise_target(
        flipped,
        swapped["delta_tag"],
        swapped.get("gold_action_mode", swapped.get("gold_action", "")),
        hard_axis=swapped.get("hard_axis"),
        scope_error_direction=swapped.get("scope_error_direction"),
        required_granularity=gold_judgment.get("required_granularity") if isinstance(gold_judgment, dict) else None,
    )
    return swapped


def flip_winner(winner: str) -> str:
    if winner == "A":
        return "B"
    if winner == "B":
        return "A"
    raise ValueError(f"winner must be A or B, got {winner!r}")


def pairwise_manifest(records: list[dict[str, Any]], dataset_path: str, forbidden_source_ids: set[str]) -> dict[str, Any]:
    delta_counts: dict[str, int] = {}
    expanded_delta_counts: dict[str, int] = {}
    gold_counts: dict[str, int] = {}
    negative_counts: dict[str, int] = {}
    hard_axis_counts: dict[str, int] = {}
    scope_error_direction_counts: dict[str, int] = {}
    winner_counts: dict[str, int] = {}
    position_variant_counts: dict[str, int] = {}
    for record in records:
        winner_counts[record["winner"]] = winner_counts.get(record["winner"], 0) + 1
        variant = record.get("position_variant")
        if isinstance(variant, str) and variant:
            position_variant_counts[variant] = position_variant_counts.get(variant, 0) + 1
        delta_counts[record["delta_tag"]] = delta_counts.get(record["delta_tag"], 0) + 1
        for tag in record["delta_tags"]:
            expanded_delta_counts[tag] = expanded_delta_counts.get(tag, 0) + 1
        gold_counts[record["gold_action"]] = gold_counts.get(record["gold_action"], 0) + 1
        negative_counts[record["negative_action"]] = negative_counts.get(record["negative_action"], 0) + 1
        hard_axis = record.get("hard_axis", "")
        if hard_axis:
            hard_axis_counts[hard_axis] = hard_axis_counts.get(hard_axis, 0) + 1
        direction = record.get("scope_error_direction", "")
        if direction:
            scope_error_direction_counts[direction] = scope_error_direction_counts.get(direction, 0) + 1
    leaked = sorted({record["source_id"] for record in records} & forbidden_source_ids)
    return {
        "dataset": dataset_path,
        "builder_versions": sorted({record.get("builder_version", "unknown") for record in records}),
        "total_pairs": len(records),
        "source_examples": len({record["source_id"] for record in records}),
        "delta_tag_counts": dict(sorted(delta_counts.items())),
        "expanded_delta_tag_counts": dict(sorted(expanded_delta_counts.items())),
        "gold_action_counts": dict(sorted(gold_counts.items())),
        "negative_action_counts": dict(sorted(negative_counts.items())),
        "winner_counts": dict(sorted(winner_counts.items())),
        "position_variant_counts": dict(sorted(position_variant_counts.items())),
        "hard_axis_counts": dict(sorted(hard_axis_counts.items())),
        "scope_error_direction_counts": dict(sorted(scope_error_direction_counts.items())),
        "forbidden_source_id_overlap": leaked,
    }


def example_ids(examples: list[ReconcileExample]) -> set[str]:
    return {example.id for example in examples}


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def prompt_hashes(examples: list[ReconcileExample]) -> set[str]:
    return {prompt_hash(example.prompt) for example in examples}
