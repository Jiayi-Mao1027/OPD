# Pairwise v0.1 Rank-128 LoRA Posbalanced Compact Summary

Run: `qwen3_8b_v0_1_r128_posbalanced_compact_lr1e5_s24`

## Configuration

- model: `/data/LLM/Qwen3-8B`
- train data: `data/pairwise/reconcilebench_v0_1_train_pairwise_posbalanced.jsonl`
- target: `compact_structured_judgment`
- LoRA: rank `128`, alpha `256`
- quantization: disabled (`load_in_4bit=false`)
- max length: `1536`
- optimizer steps: `24`
- batch size: `1`
- gradient accumulation: `8`

## Training

- first loss: `4.2595`
- last loss: `0.7130`
- training peak CUDA allocated: `29339.37 MB`
- scoring peak CUDA allocated with adapter: `18322.61 MB`

GPU note: the run used visible GPU `1`. Total device memory used briefly rose above `70 GB` because another process already occupied the same card, but this LoRA run itself reported about `29.3 GB` peak allocated and finished without OOM.

## Original Dev Result

Dataset: `data/pairwise/reconcilebench_v0_1_dev_pairwise.jsonl` (`28` pairs)

| run | winner acc | fork | scope | refusal | pred A/B | A recall | B recall | side gate | avg margin |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| full_base_bf16 | 22/28 | 1/3 | 11/13 | 5/5 | 19/9 | 15/17 | 7/11 | pass | 2.3660 |
| r128_posbalanced_compact | 23/28 | 2/3 | 11/13 | 4/5 | 16/12 | 14/17 | 9/11 | pass | 0.3848 |

Interpretation: this is a limited diagnostic improvement over the earlier
collapsed LoRA smoke on the original dev slice. It improves overall winner
accuracy and fork-state while preserving scope-contract accuracy. The remaining
regression is refusal boundary, from `5/5` to `4/5`, so it is not a clean
model-quality result.

## Posbalanced Dev Result

Dataset: `data/pairwise/reconcilebench_v0_1_dev_pairwise_posbalanced.jsonl` (`56` original+swapped pairs)

| run | winner acc | fork | scope | refusal | pred A/B | A recall | B recall | swap consistency | side gate |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| full_base_bf16 | 44/56 | 4/6 | 21/26 | 10/10 | 36/20 | 26/28 | 18/28 | 18/28 | fail |
| r128_posbalanced_compact | 44/56 | 5/6 | 19/26 | 8/10 | 28/28 | 22/28 | 22/28 | 18/28 | fail |

Interpretation: position collapse is fixed (`pred A/B = 28/28`), but swap consistency remains below the current `0.70` hard gate. The adapter improves fork-state and balances A/B recall, but gives back scope-contract and refusal-boundary accuracy on the position-balanced diagnostic set.

## Decision

This run is a mixed positive diagnostic, not a final positive result.

It shows that rank-128 LoRA with position-balanced data can avoid the previous all-A/all-B collapse and can improve fork-state. It should not yet be claimed as a clean improvement because swap consistency is still `18/28 = 0.6429`, scope falls from `21/26` to `19/26` on the posbalanced diagnostic, and refusal falls from `10/10` to `8/10`.

Recommended next run: conservative rank-128 LoRA with the same posbalanced data and compact target, but lower LR and larger accumulation:

```bash
python scripts/train_pairwise_lora.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/pairwise/reconcilebench_v0_1_train_pairwise_posbalanced.jsonl \
  --output-dir outputs/train_pairwise_lora/qwen3_8b_v0_1_r128_posbalanced_compact_lr3e6_s24 \
  --target-style compact_structured_judgment \
  --max-length 1536 \
  --max-steps 24 \
  --batch-size 1 \
  --gradient-accumulation-steps 16 \
  --lr 3e-6 \
  --lora-r 128 \
  --lora-alpha 256 \
  --attn-implementation eager
```

The swap-consistency gate should remain a hard diagnostic gate for now, but this result suggests it is also partly a base-model/scoring stability issue rather than pure adapter collapse.

## Follow-up: LR and Score-Mode Comparison

The conservative follow-up run was completed as
`qwen3_8b_v0_1_r128_posbalanced_compact_lr3e6_s24_len1024` with
`--max-length 1024`, `--gradient-accumulation-steps 16`, `--lr 3e-6`,
rank-128 LoRA, and no QLoRA/full-parameter tuning.

Winner-only scoring on original dev stayed at `23/28`, with fork-state `2/3`,
scope-contract `11/13`, refusal-boundary `4/5`, and side gate pass. On
position-balanced dev it reached `43/56`, fork-state `5/6`, scope-contract
`19/26`, refusal-boundary `9/10`, `pred A/B = 29/27`, and swap consistency
`19/28`, still below the hard `0.70` gate.

A target-aligned compact scoring mode was then added to
`scripts/score_pairwise_judgments.py` as
`--score-mode compact_structured_judgment`. Under that auxiliary diagnostic, both
rank-128 adapters reach `28/28` on original dev and `56/56` on
position-balanced dev, including `28/28` swap consistency. This confirms that
the adapters learned the compact structured target, but it should be treated as
optimistic because the scored continuation contains gold metadata fields.

Detailed results are in
`reports/pairwise_v0_1_compactscore_alignment_summary.md`.
