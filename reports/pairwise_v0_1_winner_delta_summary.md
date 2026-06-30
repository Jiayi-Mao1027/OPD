# Pairwise v0.1 Winner-Delta Reduced Target Summary

Run date: 2026-07-01

Commit: `85eba50`

## Setup

- Model: `/data/LLM/Qwen3-8B`
- Training: rank-128 LoRA, no QLoRA, no full-parameter fine-tuning
- Target style: `compact_winner_delta_tag`
- Target format:

```text
WINNER: A|B
DELTA_TAG: <delta label>
```

- Train data: `data/pairwise/reconcilebench_v0_1_train_pairwise_posbalanced.jsonl`
- Steps: `24`
- Batch: `2`
- Gradient accumulation: `8`
- Effective batch: `16`
- Max length: `1024`
- Learning rate: `3e-6`
- Peak training allocation: `35752.42 MB`
- Loss: `4.3336 -> 0.7752`

GPU note: batch size was raised from the earlier batch-1 compact runs. The process peak rose from about `29.3 GB` to `35.8 GB`; total GPU1 usage during training was observed around `67 GB`, still below the preferred `70 GB+` utilization target.

## Winner-Only Scoring

| run | dataset | winner acc | fork acc | pred A/B | swap consistency | gate |
| --- | --- | ---: | ---: | --- | ---: | --- |
| full BF16 base | original dev | `22/28 = 0.7857` | `1/3 = 0.3333` | `19/9` | - | pass |
| r128 winner-delta | original dev | `22/28 = 0.7857` | `1/3 = 0.3333` | `15/13` | - | pass |
| full BF16 base | posbalanced dev | `44/56 = 0.7857` | `4/6 = 0.6667` | `36/20` | `18/28 = 0.6429` | fail |
| r128 winner-delta | posbalanced dev | `43/56 = 0.7679` | `4/6 = 0.6667` | `27/29` | `19/28 = 0.6786` | fail |

Interpretation: reduced-target LoRA improves side balance and slightly improves swap consistency versus the full BF16 base on the position-balanced set, but it does not beat base winner accuracy and still misses the `0.70` swap-consistency gate.

## Reduced Generation

| run | dataset | winner acc | fork acc | pred A/B | swap consistency | field acc | DELTA_TAG acc | gate |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| full base reduced gen | original dev | `22/28 = 0.7857` | `2/3 = 0.6667` | `21/7` | - | `0.3929` | `0/28` | pass |
| r128 winner-delta gen | original dev | `23/28 = 0.8214` | `2/3 = 0.6667` | `16/12` | - | `0.4107` | `0/28` | pass |
| full base reduced gen | posbalanced dev | `41/56 = 0.7321` | `4/6 = 0.6667` | `41/15` | `15/28 = 0.5357` | `0.3661` | `0/56` | fail |
| r128 winner-delta gen | posbalanced dev | `45/56 = 0.8036` | `5/6 = 0.8333` | `31/25` | `19/28 = 0.6786` | `0.4018` | `0/56` | fail |

Interpretation: this is the first generation-side signal where the rank-128 adapter beats the same reduced-prompt full BF16 base on winner accuracy, fork accuracy, and side balance. It still fails the swap gate by one parent pair and gets zero exact `DELTA_TAG` accuracy.

## Mismatch Finding

The reduced target fixed the field-omission problem: all runs output exactly the two expected fields. It did not fix the rationale-label problem. `DELTA_TAG` values are usually natural/action-like labels such as `safety_boundaries`, `disallowed_scope`, `safe_redirect`, `direct_answer`, or `safe_high_level`, not the current discrete labels such as `wrong_scope`, `under_refusal`, or `lost_fork_state`.

## Decision

- Keep the winner improvement as a real but still preliminary generation signal.
- Do not claim the current run as a passed method result because position-balanced swap consistency remains below gate.
- Do not continue adding metadata fields back into generation.
- Next method step should either:
  - evaluate `WINNER` generation alone as the primary behavior target and move `DELTA_TAG` to a constrained scorer, or
  - rename/rebuild the rationale labels into observable natural labels before training them as generation targets.
