# Pairwise Data Audit

Dataset: `data/pairwise/reconcilebench_v0_1_train_pairwise.jsonl`

Total pairs: `76`

## Status Counts

| group | count |
| --- | ---: |
| clean | 76 |

## Delta Tag Counts

| group | count |
| --- | ---: |
| lost_fork_state | 11 |
| missing_clarification | 12 |
| over_refusal | 1 |
| under_refusal | 10 |
| unnecessary_clarification | 4 |
| wrong_granularity | 5 |
| wrong_scope | 33 |

## Hard Axis Counts

| group | count |
| --- | ---: |
| clarification | 16 |
| fork_state | 11 |
| granularity | 5 |
| refusal_boundary | 11 |
| scope_contract | 33 |

## Scope Error Direction Counts

| group | count |
| --- | ---: |
| none | 43 |
| too_narrow | 10 |
| unsafe_specificity | 15 |
| wrong_object | 8 |
