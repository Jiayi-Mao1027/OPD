# Pairwise v0.1 Observable-Tag Adapter and Heldout Summary

Date: 2026-07-01

## Scope

This report summarizes the rank-128 LoRA `compact_winner_obs_tag` run and the
fresh fork/scope heldout check.

Training policy:

- No full-parameter fine-tuning.
- No QLoRA.
- Rank-128 LoRA only.
- GPU memory was controlled with batch size and gradient accumulation.

## Training

Adapter:

`outputs/train_pairwise_lora/qwen3_8b_v0_1_r128_posbalanced_obs_tag_lr3e6_s24_len1024_b2/adapter`

Run settings:

- Model: `/data/LLM/Qwen3-8B`
- Dataset: `data/pairwise/reconcilebench_v0_1_train_pairwise_posbalanced.jsonl`
- Target: `compact_winner_obs_tag`
- LoRA rank/alpha: `128 / 256`
- Max length: `1024`
- Max steps: `24`
- Batch size: `2`
- Gradient accumulation: `8`
- Effective batch size: `16`
- Learning rate: `3e-6`
- Quantization: disabled

Result:

- Loss: `6.4620 -> 0.7934`
- Process peak allocated CUDA memory: `35413.57 MB`
- GPU1 total observed memory during the completed run: max `78328 MB`

Batch-size note:

- A batch-size `3` probe OOMed on the first forward pass.
- The OOM log reported only `474.44 MiB` free on the visible GPU, with this
  process using `38.43 GiB` and another process using `40.19 GiB`.
- Batch size `2` is the current stable setting for this target under the active
  shared-GPU load.

## Existing Dev Eval

Reports:

- `reports/pairwise_v0_1_dev_obs_tag_adapter_generation.md`
- `reports/pairwise_v0_1_dev_posbalanced_obs_tag_adapter_generation.md`

Original dev:

| run | winner acc | fork | scope | pred A/B | OBS_TAG exact |
| --- | ---: | ---: | ---: | --- | ---: |
| fullbase_obs | `22/28 = 0.7857` | `1/3` | `11/13` | `19/9` | `0/28` |
| r128_winner_delta_obs | `23/28 = 0.8214` | `2/3` | `11/13` | `16/12` | `6/28` |
| r128_obs_tag | `23/28 = 0.8214` | `2/3` | `11/13` | `16/12` | `11/28` |

Position-balanced dev:

| run | winner acc | fork | scope | pred A/B | swap | gate | OBS_TAG exact |
| --- | ---: | ---: | ---: | --- | ---: | --- | ---: |
| fullbase_obs | `42/56 = 0.7500` | `4/6` | `19/26` | `36/20` | `16/28 = 0.5714` | fail | `0/56` |
| r128_winner_delta_obs | `44/56 = 0.7857` | `5/6` | `20/26` | `30/26` | `20/28 = 0.7143` | pass | `8/56` |
| r128_obs_tag | `44/56 = 0.7857` | `5/6` | `20/26` | `30/26` | `20/28 = 0.7143` | pass | `18/56` |

Interpretation:

- The new obs-tag adapter improves exact `OBS_TAG` support-label matching.
- It does not improve winner accuracy, fork accuracy, scope accuracy, side
  balance, or swap consistency over the existing rank-128 winner-delta adapter
  on dev.

## Fresh Fork/Scope Heldout

Heldout files:

- Source: `data/heldout/reconcilebench_v0_fork_scope_holdout.jsonl`
- Enriched: `data/heldout/reconcilebench_v0_1_fork_scope_holdout.jsonl`
- Pairwise: `data/pairwise/reconcilebench_v0_1_fork_scope_holdout_pairwise.jsonl`
- Position-balanced: `data/pairwise/reconcilebench_v0_1_fork_scope_holdout_pairwise_posbalanced.jsonl`

Dataset properties:

- 16 source examples, all Chinese.
- 8 source examples start as `continue_reasoning`.
- Pairwise: 48 records.
- Position-balanced pairwise: 96 records, 48 original and 48 swapped.
- Audit status: `96/96` position-balanced records clean.
- No source-id or prompt-hash overlap with existing v0.1 train/dev splits.

Reports:

- `reports/heldout_fork_scope_source_audit.json`
- `reports/heldout_fork_scope_pairwise_audit.md`
- `reports/pairwise_v0_1_heldout_fork_scope_obs_tag_generation.md`
- `reports/pairwise_v0_1_heldout_fork_scope_posbalanced_obs_tag_generation.md`

Original heldout:

| run | winner acc | fork | scope | pred A/B | OBS_TAG exact |
| --- | ---: | ---: | ---: | --- | ---: |
| fullbase_obs | `31/48 = 0.6458` | `12/18` | `16/25` | `30/18` | `0/48` |
| r128_winner_delta_obs | `34/48 = 0.7083` | `13/18` | `17/25` | `15/33` | `10/48` |
| r128_obs_tag | `33/48 = 0.6875` | `12/18` | `16/25` | `16/32` | `17/48` |

Position-balanced heldout:

| run | winner acc | fork | scope | pred A/B | swap | gate | OBS_TAG exact |
| --- | ---: | ---: | ---: | --- | ---: | --- | ---: |
| fullbase_obs | `61/96 = 0.6354` | `23/36` | `31/50` | `69/27` | `27/48 = 0.5625` | fail | `0/96` |
| r128_winner_delta_obs | `68/96 = 0.7083` | `25/36` | `35/50` | `42/54` | `32/48 = 0.6667` | fail | `20/96` |
| r128_obs_tag | `68/96 = 0.7083` | `24/36` | `35/50` | `44/52` | `32/48 = 0.6667` | fail | `38/96` |

## Interpretation

The heldout check gives a mixed but useful result:

- Both rank-128 adapters beat the full BF16 base on fresh fork/scope heldout.
- Both adapters improve side balance substantially compared with fullbase on
  position-balanced heldout.
- Neither adapter passes the current position-balanced swap gate on heldout:
  `32/48 = 0.6667`, below the `0.70` threshold.
- The new obs-tag adapter does not beat the existing winner-delta adapter on
  primary winner metrics. Its main improvement is exact `OBS_TAG` matching
  (`38/96` vs `20/96` on position-balanced heldout).

This should not be claimed as a passed method result. The defensible claim is:

> Rank-128 LoRA produces a fresh-heldout winner-selection signal over full
> BF16 Qwen3-8B on fork/scope pairwise judgments, but position-invariant
> consistency is still below gate. The observable tag helps support-label
> formatting, not primary pairwise behavior.

## Swap-Failure Follow-Up

Report:

- `reports/pairwise_v0_1_heldout_fork_scope_swap_failure_analysis.md`

The parent-level swap analysis makes the gate failure more concrete:

| run | inconsistent parents | locked A | locked B | main axes |
| --- | ---: | ---: | ---: | --- |
| fullbase_obs | `21/48` | 21 | 0 | scope_contract 13, fork_state 5, clarification 3 |
| r128_winner_delta_obs | `16/48` | 5 | 11 | scope_contract 9, fork_state 7 |
| r128_obs_tag | `16/48` | 6 | 10 | scope_contract 9, fork_state 6, clarification 1 |

Both adapters fix 12 of the fullbase inconsistent parents but add 7 new
inconsistent parents. Seven parents remain inconsistent across all three runs.
The adapters reduce fullbase's all-A side locking, but still fail by locking to
one candidate side on difficult scope/fork boundaries.

## Caveats

- The fresh heldout set is a small Chinese fork/scope diagnostic set, not a
  general benchmark.
- Source actions do not cover `ask_clarification`, `direct_answer`, or `refuse`.
- `continue_reasoning` source examples are mapped into visible
  `primary_action`/`gold_action` labels for pairwise comparison.
- Historical train/dev pairwise JSONL files still contain the earlier
  `render_card` newline bug where decision-card fields can be concatenated.
  The new heldout pairwise files were regenerated after the fix. Do not
  retroactively claim historical training used the fixed rendering.

## Next Recommendation

Do not continue training the current obs-tag target as the main path yet.

Next work should focus on:

1. Response-level assistant generation/audit for the best current adapter and
   fullbase.
2. Inspect the seven persistent heldout swap failures and the seven adapter-new
   failures, especially scope-contract unsafe-specificity and fork-preservation
   cases.
3. A training objective or data construction change that directly improves
   position-invariant pairwise consistency.

## Response-Level Follow-Up

Report:

- `reports/response_level_v0_1_heldout_fork_scope_audit.md`

Scripts:

- `scripts/generate_response_level_outputs.py`
- `scripts/audit_response_level_outputs.py`

First heldout response-level smoke:

| run | overall pass | allowed action | scope pass | manual review |
| --- | ---: | ---: | ---: | ---: |
| fullbase | `6/16 = 0.3750` | `8/16 = 0.5000` | `8/16 = 0.5000` | `10/16 = 0.6250` |
| r128_winner_delta | `3/16 = 0.1875` | `6/16 = 0.3750` | `6/16 = 0.3750` | `13/16 = 0.8125` |
| r128_obs_tag | `5/16 = 0.3125` | `7/16 = 0.4375` | `7/16 = 0.4375` | `11/16 = 0.6875` |

Caveat: this is a heuristic triage audit, not a final safety judge.

Interpretation: the first assistant-facing check does not show transfer from
the pairwise winner signal to stronger generated responses. Fullbase is ahead
on this small heldout response-level heuristic audit, while both adapters have
more manual-review flags.
