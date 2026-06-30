from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
import random
from pathlib import Path
from typing import Iterable

from .schema import ACTION_MODES, SCENARIO_TYPES, ReconcileExample, dump_jsonl


def audit_examples(examples: list[ReconcileExample]) -> dict[str, object]:
    ids = [example.id for example in examples]
    duplicate_ids = sorted([example_id for example_id, count in Counter(ids).items() if count > 1])
    return {
        "total": len(examples),
        "duplicate_ids": duplicate_ids,
        "action_mode_counts": count_field(examples, "action_mode"),
        "scenario_type_counts": count_field(examples, "scenario_type"),
        "risk_category_counts": count_field(examples, "risk_category"),
        "language_counts": count_field(examples, "language"),
        "missing_action_modes": sorted(ACTION_MODES - {example.action_mode for example in examples}),
        "missing_scenario_types": sorted(SCENARIO_TYPES - {example.scenario_type for example in examples}),
        "action_mode_by_scenario_type": nested_count(examples, "scenario_type", "action_mode"),
        "action_mode_by_risk_category": nested_count(examples, "risk_category", "action_mode"),
    }


def make_action_mode_split(
    examples: list[ReconcileExample],
    dev_ratio: float = 0.25,
    seed: int = 20260630,
) -> tuple[list[ReconcileExample], list[ReconcileExample]]:
    if not 0 < dev_ratio < 1:
        raise ValueError("dev_ratio must be between 0 and 1")

    grouped: dict[str, list[ReconcileExample]] = defaultdict(list)
    for example in examples:
        grouped[example.action_mode].append(example)

    rng = random.Random(seed)
    train: list[ReconcileExample] = []
    dev: list[ReconcileExample] = []
    for action_mode in sorted(grouped):
        group = sorted(grouped[action_mode], key=lambda example: example.id)
        rng.shuffle(group)
        dev_count = round(len(group) * dev_ratio)
        if len(group) >= 2:
            dev_count = max(1, dev_count)
        else:
            dev_count = 0
        dev.extend(group[:dev_count])
        train.extend(group[dev_count:])

    return sorted(train, key=lambda example: example.id), sorted(dev, key=lambda example: example.id)


def write_examples(examples: Iterable[ReconcileExample], path: str | Path) -> None:
    records = [asdict(example) for example in examples]
    dump_jsonl(records, path)


def count_field(examples: list[ReconcileExample], field: str) -> dict[str, int]:
    return dict(sorted(Counter(getattr(example, field) for example in examples).items()))


def nested_count(examples: list[ReconcileExample], outer: str, inner: str) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for example in examples:
        counts[getattr(example, outer)][getattr(example, inner)] += 1
    return {key: dict(sorted(value.items())) for key, value in sorted(counts.items())}
