# Pairwise v0.1 Observable-Tag Generation Summary

Date: 2026-07-01

This eval-only check uses the new `compact_winner_obs_tag` target:

```text
WINNER: A|B
OBS_TAG: <observable winner-action tag>
```

It compares full BF16 Qwen3-8B with the existing rank-128 winner-delta adapter:

`outputs/train_pairwise_lora/qwen3_8b_v0_1_r128_posbalanced_winner_delta_lr3e6_s24_len1024_b2/adapter`

No QLoRA, no full-parameter fine-tuning, and no new training were used in this check.

## Summary

| dataset | run | winner acc | fork acc | scope acc | pred A/B | swap consistency | bias gate | compact field acc | full target match |
| --- | --- | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: |
| original dev | fullbase_obs | 22/28 = 0.7857 | 1/3 = 0.3333 | 11/13 = 0.8462 | 19/9 | - | pass | 0.3929 | 0.0000 |
| original dev | r128_winner_delta_obs | 23/28 = 0.8214 | 2/3 = 0.6667 | 11/13 = 0.8462 | 16/12 | - | pass | 0.5179 | 0.2143 |
| posbalanced dev | fullbase_obs | 42/56 = 0.7500 | 4/6 = 0.6667 | 19/26 = 0.7308 | 36/20 | 16/28 = 0.5714 | fail | 0.3750 | 0.0000 |
| posbalanced dev | r128_winner_delta_obs | 44/56 = 0.7857 | 5/6 = 0.8333 | 20/26 = 0.7692 | 30/26 | 20/28 = 0.7143 | pass | 0.4643 | 0.1429 |

## Interpretation

The observable-tag generation prompt gives the existing rank-128 adapter the first generation-side result that passes the position-balanced bias gate:

- winner accuracy improves over full BF16 base on both original dev and position-balanced dev;
- fork-state accuracy improves from `4/6` to `5/6` on position-balanced dev;
- position-balanced swap consistency improves from `16/28` to `20/28`, crossing the current `0.70` gate;
- side balance improves from `36/20` to `30/26`.

This is a positive pairwise generation diagnostic, not a final assistant-safety result.

The support label is still weak:

- original dev `OBS_TAG` exact accuracy is `0/28` for full base and `6/28` for the adapter;
- position-balanced dev `OBS_TAG` exact accuracy is `0/56` for full base and `8/56` for the adapter.

Use `WINNER` generation, side balance, and parent-level swap consistency as the primary gates. Treat `OBS_TAG` as an auxiliary support target until its ontology or scoring path is improved.

## Artifacts

- `reports/pairwise_v0_1_dev_obs_tag_generation.md`
- `reports/pairwise_v0_1_dev_obs_tag_generation.json`
- `reports/pairwise_v0_1_dev_obs_tag_generation_errors.csv`
- `reports/pairwise_v0_1_dev_posbalanced_obs_tag_generation.md`
- `reports/pairwise_v0_1_dev_posbalanced_obs_tag_generation.json`
- `reports/pairwise_v0_1_dev_posbalanced_obs_tag_generation_errors.csv`
- remote run log: `outputs/run_logs/obs_tag_eval_20260701_0545.log`
