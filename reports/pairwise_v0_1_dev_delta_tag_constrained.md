# Pairwise DELTA_TAG Constrained Evaluation

This report scores the rationale tag separately from winner selection. It conditions on the gold winner and therefore measures metadata target alignment, not end-to-end assistant behavior.

## Summary

| run | accuracy | missing | top predictions |
| --- | ---: | ---: | --- |
| full_base | 6/28 = 0.2143 | 0 | wrong_granularity:10, over_refusal:8, wrong_redirect:3, wrong_scope:3, unnecessary_clarification:2 |
| r128_winner_delta | 6/28 = 0.2143 | 0 | wrong_granularity:11, over_refusal:10, lost_fork_state:2, wrong_scope:2, under_refusal:1 |

## By Expected DELTA_TAG

### full_base

| expected | accuracy | top predicted labels |
| --- | ---: | --- |
| lost_fork_state | 1/3 = 0.3333 | lost_fork_state:1, over_refusal:1, wrong_granularity:1 |
| missing_clarification | 0/4 = 0.0000 | over_refusal:1, unnecessary_clarification:1, wrong_granularity:1, wrong_redirect:1 |
| over_refusal | 0/1 = 0.0000 | wrong_redirect:1 |
| under_refusal | 0/4 = 0.0000 | over_refusal:2, wrong_redirect:1, wrong_scope:1 |
| unnecessary_clarification | 1/1 = 1.0000 | unnecessary_clarification:1 |
| wrong_granularity | 2/2 = 1.0000 | wrong_granularity:2 |
| wrong_scope | 2/13 = 0.1538 | wrong_granularity:6, over_refusal:4, wrong_scope:2, under_refusal:1 |

### r128_winner_delta

| expected | accuracy | top predicted labels |
| --- | ---: | --- |
| lost_fork_state | 1/3 = 0.3333 | lost_fork_state:1, over_refusal:1, wrong_granularity:1 |
| missing_clarification | 0/4 = 0.0000 | over_refusal:3, wrong_granularity:1 |
| over_refusal | 1/1 = 1.0000 | over_refusal:1 |
| under_refusal | 0/4 = 0.0000 | lost_fork_state:1, over_refusal:1, wrong_redirect:1, wrong_scope:1 |
| unnecessary_clarification | 1/1 = 1.0000 | unnecessary_clarification:1 |
| wrong_granularity | 2/2 = 1.0000 | wrong_granularity:2 |
| wrong_scope | 1/13 = 0.0769 | wrong_granularity:7, over_refusal:4, under_refusal:1, wrong_scope:1 |

## By Hard Axis

### full_base

| hard axis | accuracy |
| --- | ---: |
| clarification | 1/5 = 0.2000 |
| fork_state | 1/3 = 0.3333 |
| granularity | 2/2 = 1.0000 |
| refusal_boundary | 0/5 = 0.0000 |
| scope_contract | 2/13 = 0.1538 |

### r128_winner_delta

| hard axis | accuracy |
| --- | ---: |
| clarification | 1/5 = 0.2000 |
| fork_state | 1/3 = 0.3333 |
| granularity | 2/2 = 1.0000 |
| refusal_boundary | 1/5 = 0.2000 |
| scope_contract | 1/13 = 0.0769 |

