# Pairwise v0.1 Compactscore Alignment Summary

This report compares two constrained scoring modes for the same rank-128 LoRA
adapters:

- `winner_only`: scores only `WINNER: A` vs `WINNER: B`.
- `compact_structured_judgment`: scores the full compact training target:
  `WINNER`, `GOLD_ACTION`, `HARD_AXIS`, `DELTA_TAG`, and optional scope,
  granularity, and fork-policy fields.

The compact score mode is a target-alignment diagnostic. It is useful for
checking whether the adapter learned the structured judgment target, but it is
optimistic because the scored continuation contains gold metadata from the pair
record. It should not be used alone as evidence that the model's generated
assistant behavior is safer.

## Runs

All adapters use `/data/LLM/Qwen3-8B`, non-quantized rank-128 LoRA, and
position-balanced pairwise training data.

| run | output dir | max length | steps | grad acc | lr | first loss | last loss | peak allocated |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `r128_lr1e5` | `outputs/train_pairwise_lora/qwen3_8b_v0_1_r128_posbalanced_compact_lr1e5_s24` | 1536 | 24 | 8 | `1e-5` | 4.2595 | 0.7130 | 29339 MB |
| `r128_lr3e6_len1024` | `outputs/train_pairwise_lora/qwen3_8b_v0_1_r128_posbalanced_compact_lr3e6_s24_len1024` | 1024 | 24 | 16 | `3e-6` | 4.6049 | 2.2657 | 29269 MB |

The second run reduced `--max-length` to 1024 and increased accumulation so the
total selected-GPU memory stayed below the 70 GB caution threshold during the
run. No QLoRA or full-parameter tuning was used.

## Winner-Only Result

Original dev:

| run | winner acc | fork | scope | refusal | pred A/B | side gate | avg margin |
| --- | ---: | ---: | ---: | ---: | --- | --- | ---: |
| `full_base_bf16` | 22/28 | 1/3 | 11/13 | 5/5 | 19/9 | pass | 2.3660 |
| `r128_lr1e5` | 23/28 | 2/3 | 11/13 | 4/5 | 16/12 | pass | 0.3848 |
| `r128_lr3e6_len1024` | 23/28 | 2/3 | 11/13 | 4/5 | 16/12 | pass | 0.5888 |

Position-balanced dev:

| run | winner acc | fork | scope | refusal | pred A/B | swap consistency | side gate |
| --- | ---: | ---: | ---: | ---: | --- | ---: | --- |
| `full_base_bf16` | 44/56 | 4/6 | 21/26 | 10/10 | 36/20 | 18/28 | fail |
| `r128_lr1e5` | 44/56 | 5/6 | 19/26 | 8/10 | 28/28 | 18/28 | fail |
| `r128_lr3e6_len1024` | 43/56 | 5/6 | 19/26 | 9/10 | 29/27 | 19/28 | fail |

Winner-only scoring shows that the adapters fix candidate-side collapse and
improve fork-state, but they still fail the current swap-consistency gate on the
position-balanced diagnostic set.

Parent-level swap analysis shows that this is not a simple A/B collapse. The
two LR settings share eight failing parent pairs, and failures concentrate in
`scope_contract / wrong_scope`, especially `unsafe_specificity`. The aggregated
winner-only swap-fail events are:

| group | lr1e-5 | lr3e-6_len1024 | total |
| --- | ---: | ---: | ---: |
| all inconsistent parents | 10 | 9 | 19 |
| `scope_contract / wrong_scope` | 5 | 5 | 10 |
| `refusal_boundary / under_refusal` | 2 | 1 | 3 |
| `clarification / missing_clarification` | 1 | 1 | 2 |
| `fork_state / lost_fork_state` | 1 | 1 | 2 |
| `granularity / wrong_granularity` | 1 | 1 | 2 |

The useful next diagnostic is therefore parent-level swap inspection and
scope-taxonomy review, not more steps on the same target.

## Compact Structured Score Result

Original dev:

| run | winner acc | fork | scope | pred A/B | side gate | avg margin |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| `full_base_compactscore` | 14/28 | 0/3 | 5/13 | 11/17 | fail | 0.0490 |
| `r128_lr1e5_compactscore` | 28/28 | 3/3 | 13/13 | 17/11 | pass | 0.1752 |
| `r128_lr3e6_len1024_compactscore` | 28/28 | 3/3 | 13/13 | 17/11 | pass | 0.1718 |

Position-balanced dev:

| run | winner acc | fork | scope | pred A/B | A recall | B recall | swap consistency | side gate |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| `full_base_compactscore` | 26/56 | 1/6 | 8/26 | 26/30 | 12/28 | 14/28 | 18/28 | fail |
| `r128_lr1e5_compactscore` | 56/56 | 6/6 | 26/26 | 28/28 | 28/28 | 28/28 | 28/28 | pass |
| `r128_lr3e6_len1024_compactscore` | 56/56 | 6/6 | 26/26 | 28/28 | 28/28 | 28/28 | 28/28 | pass |

This confirms that both adapters learned the compact structured target. The
lower learning-rate run does not improve target-aligned accuracy over the first
run; it only raises the winner-only average margin slightly while keeping
similar axis behavior.

## Decision

Current status: strong target-alignment diagnostic, not a final safety result.

The main engineering takeaway is that `winner_only` under-scores adapters trained
to emit a multi-field compact target, while `compact_structured_judgment` can be
too close to the training labels. The next useful validation is therefore not
another blind LoRA run. The next step should be one of:

1. Greedy generation parsing on the compact target, then evaluating each emitted
   field instead of logprob scoring hidden gold fields.
2. A held-out pairwise set with newly written fork/scope cases and the same
   position-balanced swap gate.
3. An external judge or human audit over generated assistant-facing responses,
   especially for `fork_state` and `scope_contract`.

Until one of those passes, the conservative claim is:

> Rank-128 LoRA on position-balanced data can learn the compact
> judgment-delta target and avoid simple candidate-side collapse, but current
> evidence is still a diagnostic result rather than proof of safer generated
> behavior.
