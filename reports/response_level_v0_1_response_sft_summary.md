# Response-Level Rank-128 LoRA SFT Summary

Date: 2026-07-01

## Purpose

This run tests whether direct source-prompt to final-response SFT can transfer
ReconcileBench v0.1 supervision into assistant-facing heldout behavior.

This is intentionally separate from the pairwise adapters:

- base model: `/data/LLM/Qwen3-8B`
- training data: `data/splits/reconcilebench_v0_1_train.jsonl`
- heldout data: `data/heldout/reconcilebench_v0_1_fork_scope_holdout.jsonl`
- no full-parameter fine-tuning
- no QLoRA / no 4-bit loading
- rank-128 LoRA only

## Implementation

New trainer:

- `scripts/train_response_lora.py`
- tests: `tests/test_response_lora.py`

Local verification:

- `pytest -q` -> `75 passed`

Remote verification:

- `python -m pytest -q tests/test_response_lora.py tests/test_response_level.py` -> `13 passed`

The training prompt contains only:

- generic response-level system prompt
- source user prompt

It does not include `final_response`, `judgment_delta`, revised labels,
allowed/disallowed fields, or action labels in the input prompt. The target is
only the reference `final_response`.

## Training Run

Output directory, ignored by Git:

`outputs/train_response_lora/qwen3_8b_v0_1_r128_final_response_lr3e6_s12_len768_b1_gc`

Key config:

- `lora_r=128`
- `lora_alpha=256`
- `lora_dropout=0.05`
- `max_length=768`
- `max_steps=12`
- `batch_size=1`
- `gradient_accumulation_steps=16`
- `lr=3e-6`
- `attn_implementation=eager`
- `gradient_checkpointing=true`
- `load_in_4bit=false`
- `full_parameter_finetune=false`

Training metrics:

- first loss: `7.0888`
- last loss: `4.1816`
- trainable parameters: `349,175,808`
- total parameters: `8,539,911,168`
- trainable fraction: `0.0409`
- process CUDA peak allocated: `22,394.38 MB`
- observed total GPU1 memory during training: about `64,640 MB`

The server was already under shared GPU load. Batch size was kept at `1` with
gradient checkpointing to keep total observed GPU memory below `70 GB`.

## Heldout Results

Strict auditor behavior:

- direct generations audit only visible text after a closed `</think>` if a
  thinking block is present.
- missing thinking close is a parse failure.
- reports exclude raw generations and reference responses by default.

### Direct1024 With Enable Thinking

Report:

`reports/response_level_v0_1_heldout_response_sft_direct1024_audit.md`

| run | overall | allowed action | scope pass | parse fail | manual review |
| --- | ---: | ---: | ---: | ---: | ---: |
| fullbase_direct1024 | 5/16 | 7/16 | 7/16 | 0 | 11/16 |
| r128_winner_delta_direct1024 | 3/16 | 4/16 | 5/16 | 0 | 13/16 |
| r128_obs_tag_direct1024 | 4/16 | 6/16 | 7/16 | 0 | 12/16 |
| r128_response_sft_direct1024 | 4/16 | 5/16 | 7/16 | 0 | 12/16 |

The response-SFT adapter does not beat fullbase. It ties the obs-tag adapter on
overall pass but has lower allowed-action match and one disallowed-content flag.

### Direct1024 Without Enable Thinking

Report:

`reports/response_level_v0_1_heldout_response_sft_direct1024_no_think_audit.md`

| run | overall | allowed action | scope pass | parse fail | manual review |
| --- | ---: | ---: | ---: | ---: | ---: |
| fullbase_direct1024_no_think | 7/16 | 9/16 | 10/16 | 0 | 9/16 |
| r128_response_sft_direct1024_no_think | 5/16 | 7/16 | 9/16 | 0 | 11/16 |

Matched no-thinking evaluation is still negative. The full BF16 base remains
stronger than the response-SFT adapter.

## Interpretation

This is a negative result for the first response-level SFT path:

> A 12-step rank-128 final-response LoRA on the 38-example v0.1 train split does
> not improve assistant-facing heldout behavior over full BF16 Qwen3-8B.

The result should not be framed as a Reconcile-OPSD method success. It also
should not be over-interpreted as a project-level failure. The likely limiting
factors are small response-level data, short reference responses, sparse
fork/scope coverage, and the fact that final-response SFT may learn surface
safety phrasing without stable boundary selection.

The strongest current response-level baseline is still fullbase no-thinking
direct1024 at `7/16` on this heuristic audit.

## Next Recommended Step

Do not continue by simply adding more steps on the same 38 final responses.

Recommended next path:

1. Manually or externally judge the response-level failure rows.
2. Build response-level paired good/bad final responses for persistent
   fork/scope failures.
3. Consider response-level preference training or prefix-level fork-preservation
   targets after the failure map is reviewed.

