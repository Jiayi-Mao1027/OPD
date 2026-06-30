# Pairwise Data Audit

Dataset: `data\pairwise\reconcilebench_v0_1_train_pairwise_posbalanced.jsonl`

Total pairs: `152`

## Status Counts

| group | count |
| --- | ---: |
| clean | 152 |

## Delta Tag Counts

| group | count |
| --- | ---: |
| lost_fork_state | 22 |
| missing_clarification | 24 |
| over_refusal | 2 |
| under_refusal | 20 |
| unnecessary_clarification | 8 |
| wrong_granularity | 10 |
| wrong_scope | 66 |

## Hard Axis Counts

| group | count |
| --- | ---: |
| clarification | 32 |
| fork_state | 22 |
| granularity | 10 |
| refusal_boundary | 22 |
| scope_contract | 66 |

## Scope Error Direction Counts

| group | count |
| --- | ---: |
| none | 86 |
| too_narrow | 20 |
| unsafe_specificity | 30 |
| wrong_object | 16 |
