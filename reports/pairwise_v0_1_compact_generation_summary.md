# Pairwise v0.1 Compact Generation Summary

Date: 2026-07-01

This report checks whether the high `compact_structured_judgment` logprob
alignment scores transfer to actual greedy compact-target generation under the
current winner and position-consistency gates. They do not.

The generation path asks the model to emit the compact target format directly
and then parses the generated text into `WINNER`, `GOLD_ACTION`, `HARD_AXIS`,
`DELTA_TAG`, `SCOPE_ERROR_DIRECTION`, `REQUIRED_GRANULARITY`, and
`FORK_POLICY`. The parse result is evaluated with the same pairwise report
tooling used for score files.

## Inputs

Datasets:

- `data/pairwise/reconcilebench_v0_1_dev_pairwise.jsonl`
- `data/pairwise/reconcilebench_v0_1_dev_pairwise_posbalanced.jsonl`

Runs:

- `full_base_gen`: Qwen3-8B full BF16 base, no adapter.
- `r128_lr1e5_gen`: rank-128 non-QLoRA LoRA, compact target, `lr=1e-5`,
  24 steps.
- `r128_lr3e6_len1024_gen`: rank-128 non-QLoRA LoRA, compact target,
  `lr=3e-6`, `max_length=1024`, 24 steps.

Generation used greedy decoding (`do_sample=false`) and did not use 4-bit
loading.

Reports:

- `reports/pairwise_v0_1_dev_compact_generation_compare.md`
- `reports/pairwise_v0_1_dev_posbalanced_compact_generation_compare.md`

## Original Dev

| run | winner acc | fork acc | scope acc | pred A/B | bias gate | compact field acc | full target match |
| --- | ---: | ---: | ---: | --- | --- | ---: | ---: |
| full_base_gen | 23/28 = 0.8214 | 1/3 = 0.3333 | 11/13 = 0.8462 | 16/12 | pass | 0.1173 | 0.0000 |
| r128_lr1e5_gen | 20/28 = 0.7143 | 1/3 = 0.3333 | 9/13 = 0.6923 | 11/17 | fail | 0.4439 | 0.0000 |
| r128_lr3e6_len1024_gen | 22/28 = 0.7857 | 1/3 = 0.3333 | 11/13 = 0.8462 | 15/13 | pass | 0.1122 | 0.0000 |

## Position-Balanced Dev

| run | winner acc | fork acc | scope acc | pred A/B | swap consistency | bias gate | compact field acc | full target match |
| --- | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: |
| full_base_gen | 43/56 = 0.7679 | 4/6 = 0.6667 | 20/26 = 0.7692 | 31/25 | 19/28 = 0.6786 | fail | 0.1097 | 0.0000 |
| r128_lr1e5_gen | 39/56 = 0.6964 | 4/6 = 0.6667 | 17/26 = 0.6538 | 19/37 | 15/28 = 0.5357 | fail | 0.4260 | 0.0000 |
| r128_lr3e6_len1024_gen | 42/56 = 0.7500 | 4/6 = 0.6667 | 19/26 = 0.7308 | 28/28 | 18/28 = 0.6429 | fail | 0.1071 | 0.0000 |

Note: the report decimal for full-base swap consistency is `0.6786`, which is
`19/28`.

## Interpretation

The earlier `compact_structured_judgment` score-mode result was correctly
classified as an auxiliary, label-conditioned target-alignment diagnostic. Its
100% dev score does not survive actual compact generation.

Current rank-128 LoRA result is negative under generation:

- Neither adapter beats the full BF16 base on winner accuracy.
- Neither adapter beats the full BF16 base on position-balanced swap
  consistency.
- Neither adapter produces any exact full compact target matches under the
  current strict all-field metric.
- `r128_lr1e5_gen` learns more non-winner compact fields, but regresses winner
  accuracy, scope-contract accuracy, and side balance.
- `r128_lr3e6_len1024_gen` is the less-bad adapter candidate because it avoids
  the strong B skew and stays closer to base, but it still does not clear the
  position-balanced gate.

This should be treated as a calibration result, not a positive method result.

Follow-up mismatch analysis is in
`reports/pairwise_v0_1_compact_generation_mismatch_analysis.md`.

That analysis shows `full target match = 0.0000` is too strict to use as a
standalone behavioral metric. It is still a useful schema diagnostic:

- full base and `r128_lr3e6_len1024` mostly generate only `WINNER` plus a
  `DELTA_TAG` value that often looks like an action label;
- `r128_lr1e5` emits nearly all compact fields, but `HARD_AXIS`,
  `DELTA_TAG`, and `SCOPE_ERROR_DIRECTION` are schema-confused;
- the next fix should target prompt/label ontology and target design, not more
  training steps on the same compact target.

## Next Actions

1. Redesign the compact target/prompt so the label ontology is explicit and the
   model is not asked to infer arbitrary gold metadata fields without support.
2. Keep `winner_only` and position-balanced swap consistency as the primary
   gate. Do not promote compactscore or compact field accuracy to the main
   safety metric.
3. If training continues, use rank-128 LoRA only. Prefer the lower-learning-rate
   `lr3e-6_len1024` setting as the starting point, then vary seeds and small
   hyperparameters while controlling memory with batch size, gradient
   accumulation, and sequence length.
4. Build a fresh held-out fork/scope-focused validation set before claiming any
   method improvement.
