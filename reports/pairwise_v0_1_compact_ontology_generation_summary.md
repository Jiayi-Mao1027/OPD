# Pairwise v0.1 Compact Ontology Generation Summary

Date: 2026-07-01

This report evaluates an explicit-label ontology prompt for compact generation.
It is eval-only: no training, no QLoRA, and no full-parameter tuning.

The ontology prompt keeps the same compact target and output parser, but lists
allowed labels for `GOLD_ACTION`, `HARD_AXIS`, `DELTA_TAG`,
`SCOPE_ERROR_DIRECTION`, `REQUIRED_GRANULARITY`, and `FORK_POLICY`. It was added
to test whether the previous compact generation failures were mainly caused by
an underspecified label space.

## Reports

- `reports/pairwise_v0_1_dev_compact_ontology_generation_compare.md`
- `reports/pairwise_v0_1_dev_posbalanced_compact_ontology_generation_compare.md`
- `reports/pairwise_v0_1_compact_ontology_generation_mismatch_analysis.md`

## Original Dev

| run | minimal winner acc | ontology winner acc | minimal field acc | ontology field acc | ontology full match | ontology pred A/B |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| full base | 23/28 = 0.8214 | 15/28 = 0.5357 | 0.1173 | 0.0867 | 0.0000 | 6/22 |
| r128 lr1e-5 | 20/28 = 0.7143 | 15/28 = 0.5357 | 0.4439 | 0.5153 | 0.1071 | 4/24 |
| r128 lr3e-6 len1024 | 22/28 = 0.7857 | 14/28 = 0.5000 | 0.1122 | 0.0867 | 0.0000 | 5/23 |

## Position-Balanced Dev

| run | minimal winner acc | ontology winner acc | minimal swap | ontology swap | minimal field acc | ontology field acc | ontology full match | ontology pred A/B |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| full base | 43/56 = 0.7679 | 34/56 = 0.6071 | 0.6786 | 0.5000 | 0.1097 | 0.1046 | 0.0000 | 16/40 |
| r128 lr1e-5 | 39/56 = 0.6964 | 36/56 = 0.6429 | 0.5357 | 0.3571 | 0.4260 | 0.5510 | 0.0893 | 10/46 |
| r128 lr3e-6 len1024 | 42/56 = 0.7500 | 35/56 = 0.6250 | 0.6429 | 0.3929 | 0.1071 | 0.1046 | 0.0000 | 13/43 |

## Mismatch Findings

The ontology prompt changes the failure mode, but does not solve the method
problem.

- Full base and `r128_lr3e6_len1024` still average only `2.00` parsed fields:
  mostly `WINNER` plus `DELTA_TAG`.
- `r128_lr1e5` still emits the most complete compact target, with about `6.6`
  parsed fields per row, but it becomes strongly B-skewed.
- `r128_lr1e5` improves strict full-target exact match from `0.0000` to
  `0.1071` on original dev and `0.0893` on position-balanced dev.
- The mismatch analyzer reports no schema-level confusion labels under the
  ontology prompt, so explicit label lists did reduce field-name/action-label
  confusions.
- Winner selection regresses sharply for every run, and position-balanced swap
  consistency gets worse. This means the longer ontology prompt is not a usable
  primary generation prompt.

## Interpretation

The previous compact generation failure was partly a label-ontology problem,
but not only a label-ontology problem.

Explicit labels can make `r128_lr1e-5` emit more valid metadata fields, but the
same prompt distracts or biases winner selection. The current one-shot compact
target is therefore overloaded: it asks the model to choose the better card and
predict several metadata fields in a single free generation.

The next method step should not be more rank-128 LoRA steps on the same compact
target. A better direction is to decouple the targets:

1. keep pairwise winner selection as the primary safety gate;
2. treat metadata fields as auxiliary diagnostics or separate constrained
   scoring tasks;
3. if generation is needed, generate `WINNER` first, then optionally generate
   a small rationale tag set with explicit labels.

## Recommendation

Do not use `--prompt-style ontology` as the default compact generation prompt.
Keep it as a diagnostic prompt that tests label-space sensitivity.

The next runnable experiment should be either:

- a reduced generation target such as `WINNER` plus one observable rationale
  tag, evaluated against the same position-balanced gate; or
- a constrained multi-field scorer that scores each compact field from a fixed
  label list without asking the model to emit all fields at once.
