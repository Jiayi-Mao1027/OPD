# Rank128 LoRA Position-Balanced Runs

This project stage uses rank-128 LoRA only.

Do not use full-parameter fine-tuning for pairwise judgment experiments. Do not use QLoRA or `--load-in-4bit` for official runs in this stage. Control GPU memory with `--batch-size`, `--gradient-accumulation-steps`, and `--max-length`.

## Data

Use the position-balanced train file for new LoRA runs:

```bash
data/pairwise/reconcilebench_v0_1_train_pairwise_posbalanced.jsonl
```

Use the original dev file for continuity with earlier reports, and the position-balanced dev file for side-bias and swap-consistency gates:

```bash
data/pairwise/reconcilebench_v0_1_dev_pairwise.jsonl
data/pairwise/reconcilebench_v0_1_dev_pairwise_posbalanced.jsonl
```

The position-balanced train file has 152 rows: 76 original and 76 swapped. Winner positions are exactly balanced at A=76 and B=76.

## First Sanity Run

```bash
python scripts/train_pairwise_lora.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/pairwise/reconcilebench_v0_1_train_pairwise_posbalanced.jsonl \
  --output-dir outputs/train_pairwise_lora/qwen3_8b_v0_1_r128_posbalanced_compact_lr1e5_s24 \
  --target-style compact_structured_judgment \
  --max-length 1536 \
  --max-steps 24 \
  --batch-size 1 \
  --gradient-accumulation-steps 8 \
  --lr 1e-5 \
  --lora-r 128 \
  --lora-alpha 256
```

The command intentionally omits `--load-in-4bit`.

## Eval Gate

A run should not be treated as useful if it fails the position-bias gate:

```text
pred_A_rate > 0.75
pred_B_rate > 0.75
swap_consistency < 0.70
```

For the current base comparison, the minimum hard-axis preservation gate is:

```text
fork_state >= 1/3
scope_contract >= 10/13
refusal_boundary >= 4/5
```

The preferred success target is:

```text
fork_state >= 2/3
scope_contract >= 10/13
refusal_boundary >= 4/5
position_bias_gate = pass
```

## Scoring

Score both original dev and position-balanced dev:

```bash
python scripts/score_pairwise_judgments.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/pairwise/reconcilebench_v0_1_dev_pairwise.jsonl \
  --adapter outputs/train_pairwise_lora/qwen3_8b_v0_1_r128_posbalanced_compact_lr1e5_s24/adapter \
  --output outputs/pairwise_scores/qwen3_8b_v0_1_dev_r128_posbalanced_compact.jsonl

python scripts/score_pairwise_judgments.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/pairwise/reconcilebench_v0_1_dev_pairwise_posbalanced.jsonl \
  --adapter outputs/train_pairwise_lora/qwen3_8b_v0_1_r128_posbalanced_compact_lr1e5_s24/adapter \
  --output outputs/pairwise_scores/qwen3_8b_v0_1_dev_posbalanced_r128_posbalanced_compact.jsonl
```

Then evaluate:

```bash
python scripts/evaluate_pairwise_scores.py \
  --dataset data/pairwise/reconcilebench_v0_1_dev_pairwise_posbalanced.jsonl \
  --scores r128_posbalanced=outputs/pairwise_scores/qwen3_8b_v0_1_dev_posbalanced_r128_posbalanced_compact.jsonl \
  --output-md reports/pairwise_v0_1_dev_posbalanced_r128_compact_eval.md \
  --output-json reports/pairwise_v0_1_dev_posbalanced_r128_compact_eval.json \
  --output-csv reports/pairwise_v0_1_dev_posbalanced_r128_compact_errors.csv
```
