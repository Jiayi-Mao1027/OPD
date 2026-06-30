# Pairwise Data Audit

Source dataset: `data/heldout/reconcilebench_v0_fork_scope_holdout.jsonl`

Enriched source: `data/heldout/reconcilebench_v0_1_fork_scope_holdout.jsonl`

Source examples: `16`, all `zh`.

Source action-mode counts:

| group | count |
| --- | ---: |
| continue_reasoning | 8 |
| partial_allowed | 3 |
| safe_high_level | 3 |
| safe_redirect | 2 |

Source caveat: this is a small Chinese fork/scope diagnostic set. It does not
cover `ask_clarification`, `direct_answer`, or `refuse` as source
`action_mode` values. The `continue_reasoning` source examples are mapped into
visible `primary_action` / `gold_action` labels for pairwise comparison.

Original pairwise dataset:
`data/pairwise/reconcilebench_v0_1_fork_scope_holdout_pairwise.jsonl`

Original pairwise pairs: `48` from `16` source examples.

Position-balanced pairwise dataset:
`data/pairwise/reconcilebench_v0_1_fork_scope_holdout_pairwise_posbalanced.jsonl`

Position-balanced pairs: `96`, with `48` original and `48` swapped records.

The pairwise builder reported no forbidden source-id overlap and no forbidden
prompt-hash overlap against existing v0.1 train/dev splits.

Dataset: `data/pairwise/reconcilebench_v0_1_fork_scope_holdout_pairwise_posbalanced.jsonl`

Total pairs: `96`

## Status Counts

| group | count |
| --- | ---: |
| clean | 96 |

## Delta Tag Counts

| group | count |
| --- | ---: |
| lost_fork_state | 36 |
| unnecessary_clarification | 6 |
| wrong_redirect | 4 |
| wrong_scope | 50 |

## Hard Axis Counts

| group | count |
| --- | ---: |
| clarification | 6 |
| fork_state | 36 |
| redirect_boundary | 4 |
| scope_contract | 50 |

## Scope Error Direction Counts

| group | count |
| --- | ---: |
| none | 46 |
| too_narrow | 12 |
| unsafe_specificity | 16 |
| wrong_level | 12 |
| wrong_object | 10 |
