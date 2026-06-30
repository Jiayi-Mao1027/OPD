# Pairwise v0.1 Plan

Last updated: 2026-07-01 00:52 +08:00

## Decision

Do not move directly from the v0 pairwise base result to a full pairwise QLoRA
run.

Use a hybrid path:

1. Repair the target/schema around fork state and answer scope.
2. Re-score Qwen3-8B 4-bit base with the repaired v0.1 eval.
3. Run one small structured pairwise QLoRA smoke only after the revised target is
   inspectable.

Rationale:

- Pairwise v0 has a useful signal: Qwen3-8B 4-bit base gets `19/28 = 0.6786`
  winner accuracy.
- The failures are concentrated in the project's core contribution axes:
  `lost_fork_state` is `0/4`, and `wrong_scope` is `1/4`.
- A winner-only QLoRA could improve aggregate pairwise accuracy while missing
  the actual Reconcile-OPSD claim: preserving competing forks and enforcing
  answer-scope contracts.

## Schema Repair

Keep `continue_reasoning` out of final user-visible `primary_action`.

If an old example had `primary_action = continue_reasoning`, convert it into a
visible user action plus fork-state metadata:

- `primary_action`: one of `ask_clarification`, `partial_allowed`,
  `safe_high_level`, `direct_answer`, `safe_redirect`, or `refuse`.
- `needs_more_reasoning`: `true`.
- `fork_state`: non-empty.

Add a structured fork-state object:

```json
{
  "fork_state": {
    "forks_present": [],
    "fork_resolution": "resolved | unresolved | partially_resolved",
    "fork_policy": "preserve | disambiguate | defer | select_with_uncertainty",
    "collapse_risk": "none | over_refusal | unsafe_answer | premature_redirect | premature_answer"
  }
}
```

Add a structured scope contract object:

```json
{
  "scope_contract": {
    "answerability": "full | partial | none | unclear",
    "allowed_content": [],
    "disallowed_content": [],
    "required_granularity": "full | bounded_steps | high_level | redirect_only | refuse_only",
    "scope_error_direction": "none | too_broad | too_narrow | wrong_level | wrong_object | unsafe_specificity"
  }
}
```

## Pairwise v0.1 Record Shape

Each v0.1 pair should include:

```json
{
  "pair_id": "...",
  "source_id": "...",
  "prompt_hash": "...",
  "split": "train | dev",
  "prompt": "...",
  "candidate_a": {
    "decision_card": {},
    "response_sketch": "..."
  },
  "candidate_b": {
    "decision_card": {},
    "response_sketch": "..."
  },
  "winner": "A | B",
  "delta_tag": "over_refusal | under_refusal | missing_clarification | unnecessary_clarification | wrong_scope | wrong_redirect | wrong_granularity | lost_fork_state",
  "hard_axis": "fork_state | scope_contract | clarification | refusal_boundary | redirect_boundary | granularity",
  "gold_judgment": {
    "winner": "A | B",
    "delta_tag": "...",
    "primary_action": "...",
    "needs_more_reasoning": false,
    "fork_policy": "...",
    "scope_error_direction": "...",
    "required_granularity": "..."
  }
}
```

Construction rules:

- Keep train/dev split separation and source-id/prompt-hash leakage checks.
- Drop ambiguous pairs where both candidates are acceptable.
- `lost_fork_state` pairs must compare a fork-preserving candidate against a
  fork-collapsing candidate.
- `wrong_scope` pairs must label the error direction: `too_broad`,
  `too_narrow`, `wrong_level`, `wrong_object`, or `unsafe_specificity`.

## Minimal Run Matrix

Run 1: base v0.1 scoring.

- Purpose: verify that the repaired schema and eval are usable before training.
- Success: all axis metrics are emitted, parse failure is zero, and the error
  table separates fork-state from scope-contract failures.
- Failure: the new fields are too ambiguous to score consistently.

Run 2: winner-only pairwise QLoRA smoke.

- Purpose: train a cheap baseline on the existing pairwise objective.
- Success: loss decreases, missing count remains zero, and dev winner accuracy
  does not collapse below the base control.
- Failure: aggregate accuracy improves while `lost_fork_state` and `wrong_scope`
  stay flat or regress.

Run 3: structured judgment-delta QLoRA smoke.

- Purpose: test whether explicit fork/scope fields improve the core axes.
- Success: `lost_fork_state` improves from `0/4` toward at least `2/4`, or
  `wrong_scope` improves from `1/4` toward at least `2/4`, while overall winner
  accuracy remains near the base control.
- Failure: the model learns the output format but not the hard axes.

Run 4: balanced structured judgment-delta QLoRA smoke.

- Purpose: check whether upweighting `lost_fork_state`, `wrong_scope`, and
  `partial_allowed` changes the failure profile.
- Success: hard-axis accuracy improves without destroying easy-axis accuracy.
- Failure: improvements are only from overfitting duplicated hard cases.

## Required Metrics

Every pairwise report should include:

- pairwise winner accuracy;
- source-level accuracy;
- accuracy by `delta_tag`;
- accuracy by `hard_axis`;
- accuracy by `primary_action`;
- accuracy by `scope_error_direction`;
- fork-preservation accuracy;
- scope-contract accuracy;
- average winner margin;
- missing and parse-failure counts;
- peak allocated CUDA memory.

## Engineering Checklist

Minimum data/schema work:

- Extend `src/reconcile_opsd/schema.py` with `fork_state` and
  `scope_contract` validation while keeping compatibility with existing v0
  records.
- Update `src/reconcile_opsd/pairwise_data.py` so v0.1 pairs include
  `hard_axis`, `gold_judgment`, candidate decision cards, and response sketches.
- Extend `scripts/build_pairwise_judgment_data.py` with a builder version or
  equivalent switch for pairwise v0.1.
- Generate `data/pairwise/reconcilebench_v0_1_train_pairwise.jsonl`,
  `data/pairwise/reconcilebench_v0_1_dev_pairwise.jsonl`, and matching
  manifests.
- Add a data audit report under `reports/pairwise_v0_1_data_audit.*` that marks
  clean, ambiguous, and taxonomy-problem pairs.

Minimum eval work:

- Extend `scripts/evaluate_pairwise_scores.py` with `hard_axis`,
  `scope_error_direction`, source-level accuracy, fork-preservation accuracy,
  scope-contract accuracy, and parse-failure counts.
- Re-score Qwen3-8B 4-bit base on v0.1 before adapter training.

Minimum training work:

- Add `scripts/train_pairwise_lora.py`.
- Support `--target-style winner_only|structured_judgment_delta`.
- Write `metrics.json`, `train_losses.jsonl`, `preflight_gpu.json`,
  `config_resolved.json`, and the adapter directory under ignored `outputs/`.
- Reuse `scripts/score_pairwise_judgments.py` with `--adapter` for adapter
  scoring.

Reproducibility risks to track:

- v0/v0.1 dev size is too small for a final claim; treat results as method
  smoke tests.
- Decision-card candidates are not yet full assistant responses.
- Winner-only scoring does not evaluate delta tags or scope/fork axes by itself.
- Training dependencies include `peft` and `bitsandbytes`; keep environment
  assumptions documented.
- GPU/preflight logs must be persisted into each output directory, not only
  printed to stdout.

## Framing

Main claim:

Reconcile-OPSD uses structured judgment-delta supervision to teach a small
thinking-capable model to compare competing response forks, with explicit
pressure on fork preservation and answer-scope control rather than generic
refusal calibration.

Secondary claims:

- Pairwise judgment-delta is a better first-stage learning signal than
  action-mode plus free-form rationale SFT.
- Axis-aware evaluation exposes failures that aggregate winner accuracy hides.
- `lost_fork_state` and `wrong_scope` are core diagnostic axes, not just error
  tags.

Avoid claiming:

- that v0 proves Reconcile-OPSD works;
- that pairwise QLoRA significantly improves safety before v0.1 evidence;
- that `0.6786` on 28 dev pairs is a stable generalization result;
- that this is an R1/DeepSeek route in the current stage.
