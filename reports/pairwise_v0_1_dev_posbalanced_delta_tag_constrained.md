# Pairwise DELTA_TAG Constrained Evaluation

This report scores the rationale tag separately from winner selection. It conditions on the gold winner and therefore measures metadata target alignment, not end-to-end assistant behavior.

## Summary

| run | accuracy | missing | top predictions |
| --- | ---: | ---: | --- |
| full_base | 11/56 = 0.1964 | 0 | wrong_granularity:23, over_refusal:17, wrong_scope:7, unnecessary_clarification:4, wrong_redirect:3 |
| r128_winner_delta | 10/56 = 0.1786 | 0 | wrong_granularity:26, over_refusal:19, lost_fork_state:3, unnecessary_clarification:3, wrong_scope:3 |

## By Expected DELTA_TAG

### full_base

| expected | accuracy | top predicted labels |
| --- | ---: | --- |
| lost_fork_state | 1/6 = 0.1667 | wrong_granularity:3, lost_fork_state:1, over_refusal:1, wrong_scope:1 |
| missing_clarification | 0/8 = 0.0000 | wrong_granularity:3, over_refusal:2, unnecessary_clarification:2, wrong_redirect:1 |
| over_refusal | 1/2 = 0.5000 | over_refusal:1, wrong_redirect:1 |
| under_refusal | 0/8 = 0.0000 | over_refusal:4, wrong_scope:3, wrong_redirect:1 |
| unnecessary_clarification | 2/2 = 1.0000 | unnecessary_clarification:2 |
| wrong_granularity | 4/4 = 1.0000 | wrong_granularity:4 |
| wrong_scope | 3/26 = 0.1154 | wrong_granularity:13, over_refusal:9, wrong_scope:3, under_refusal:1 |

### r128_winner_delta

| expected | accuracy | top predicted labels |
| --- | ---: | --- |
| lost_fork_state | 1/6 = 0.1667 | wrong_granularity:3, over_refusal:2, lost_fork_state:1 |
| missing_clarification | 0/8 = 0.0000 | over_refusal:4, wrong_granularity:3, unnecessary_clarification:1 |
| over_refusal | 2/2 = 1.0000 | over_refusal:2 |
| under_refusal | 0/8 = 0.0000 | lost_fork_state:2, over_refusal:2, wrong_scope:2, wrong_granularity:1, wrong_redirect:1 |
| unnecessary_clarification | 2/2 = 1.0000 | unnecessary_clarification:2 |
| wrong_granularity | 4/4 = 1.0000 | wrong_granularity:4 |
| wrong_scope | 1/26 = 0.0385 | wrong_granularity:15, over_refusal:9, under_refusal:1, wrong_scope:1 |

## By Hard Axis

### full_base

| hard axis | accuracy |
| --- | ---: |
| clarification | 2/10 = 0.2000 |
| fork_state | 1/6 = 0.1667 |
| granularity | 4/4 = 1.0000 |
| refusal_boundary | 1/10 = 0.1000 |
| scope_contract | 3/26 = 0.1154 |

### r128_winner_delta

| hard axis | accuracy |
| --- | ---: |
| clarification | 2/10 = 0.2000 |
| fork_state | 1/6 = 0.1667 |
| granularity | 4/4 = 1.0000 |
| refusal_boundary | 2/10 = 0.2000 |
| scope_contract | 1/26 = 0.0385 |

