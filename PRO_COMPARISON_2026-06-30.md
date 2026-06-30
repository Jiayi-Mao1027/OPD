# Pro Comparison: v0 Negative Result Review

## Context

Two ChatGPT Pro reviews were collected after the Qwen3-8B v0 action-mode SFT
negative results:

- The first review was in the longer `OPD安全研究现状` chat.
- The second review was in a fresh shorter chat to reduce long-context drift.

Both reviews treated the current result as a target/evaluation problem, not a
reason to continue the same SFT run.

## Shared Conclusions

- Freeze the current `ACTION_MODE + REASON` QLoRA line as a negative-result
  baseline.
- Do not add more steps to the same action-mode/REASON target.
- `continue_reasoning` should not remain a root-level terminal response action.
  Treat it as a fork-state or prefix-level control target.
- Move from free-form label generation to structured judgment:
  constrained candidate scoring, audit tables, pairwise judgment-delta data, and
  decision-card ranking.
- `final_response` should be evaluated, but not trained as the next target.
- Keep R1, larger models, large benchmark sweeps, and LoRA hyperparameter sweeps
  out of the first-stage path.

## Differences

- The longer-chat review emphasized constrained candidate scoring, top-2/margin
  diagnostics, and later mode-level judgment-delta/self-distillation.
- The fresh-chat review emphasized schema axes, allowed-action evaluation,
  error audit tables, pairwise ranker construction, and a decision-card cascade.

## Decision

Adopt the fresh-chat schema/eval restructuring first because it is the
precondition for the pairwise/delta plan. Then adopt the shared pairwise
judgment-delta target. Keep the longer-chat mode-level delta/self-distillation
idea as a later stage after constrained scoring and audit metrics are stable.

## Immediate Engineering Plan

1. Add schema support for optional decision axes such as `primary_action`,
   `acceptable_actions`, `risk_type`, `can_answer`,
   `missing_critical_info`, `allowed_scope`, `needs_clarification`,
   `needs_uncertainty_expression`, `context_conflict`, and
   `needs_more_reasoning`.
2. Add constrained action-mode scoring that scores every candidate mode by
   logprob and reports top-2, gold margin, entropy, per-mode F1, and confusion
   matrices.
3. Add an audit/report script that can compare base predictions, adapter
   predictions, and constrained score rows in one markdown report plus an error
   CSV.
4. Use the resulting error table to build clean pairwise `candidate A/B ->
   winner + delta_tag` examples.
5. Split `continue_reasoning` into a separate prefix-level fork-state task.

## Do Not Do Now

- No `20 -> 100/200/300` step continuation of the current action-mode/REASON
  QLoRA.
- No `final_response` SFT.
- No full CoT or `<think>` SFT.
- No R1 or larger-model switch.
- No large safety benchmark sweep.
- No LoRA rank/lr/batch sweep.
- No claim of method improvement from the current 14-item dev accuracy.
