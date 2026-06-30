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

## Score Mode Policy

`score-mode=winner_only` is the primary continuity metric and acceptance gate
for pairwise winner selection. The earlier `target-style=winner_only` training
run is a separate rejected training target and should not be confused with
winner-only scoring.

`score-mode=compact_structured_judgment` is auxiliary. It scores the full
compact target, including gold metadata fields from the pair record, so a
compactscore pass means target-format alignment, not proven safer assistant
behavior. A compactscore pass cannot override a failed winner-only
swap-consistency gate.

## Latest Diagnostic Result

The first position-balanced compact run is documented in
`reports/pairwise_v0_1_r128_posbalanced_compact_summary.md`.

Status: mixed positive diagnostic under `winner_only`, strong target-alignment
diagnostic under `compact_structured_judgment`.

The `lr1e-5` run improves original dev from `22/28` to `23/28`, improves
fork-state from `1/3` to `2/3`, preserves original-dev scope-contract at
`11/13`, and removes the prior all-A/all-B collapse. It is not a final positive
result under winner-only scoring because posbalanced dev swap consistency
remains `18/28 = 0.6429`, below the current `0.70` gate.

The follow-up `lr3e-6`, `max_length=1024`, grad-accum `16` run also reaches
`23/28` on original dev and raises posbalanced swap consistency only to
`19/28`, still below gate.

The target-aligned compact score mode gives `28/28` on original dev and `56/56`
on posbalanced dev for both adapters. Treat that as evidence that the adapters
learned the structured target format, not as standalone evidence of safer
generated assistant behavior. See
`reports/pairwise_v0_1_compactscore_alignment_summary.md`.

## Greedy Compact Generation Check

The generation-side check is documented in
`reports/pairwise_v0_1_compact_generation_summary.md`.

It asks the model to generate the compact target directly and parses the output.
This is a stricter check than `score-mode=compact_structured_judgment` because
the model must emit the fields instead of receiving a scored gold continuation.

Current result: negative calibration.

On original dev:

- full BF16 base: `23/28 = 0.8214` winner accuracy;
- `r128_lr1e5`: `20/28 = 0.7143`;
- `r128_lr3e6_len1024`: `22/28 = 0.7857`.

On position-balanced dev:

- full BF16 base: `43/56 = 0.7679`, swap consistency `19/28 = 0.6786`;
- `r128_lr1e5`: `39/56 = 0.6964`, swap consistency `15/28 = 0.5357`;
- `r128_lr3e6_len1024`: `42/56 = 0.7500`, swap consistency
  `18/28 = 0.6429`.

All generation runs have `0.0000` full compact-target match. The `lr1e-5`
adapter has higher compact field accuracy, but it regresses winner accuracy,
scope-contract accuracy, and side balance. The `lr3e-6_len1024` adapter is
closer to base and avoids the strong B skew, but it still does not pass the
position-balanced gate or beat base.

Do not claim that rank-128 LoRA is effective from the current compact runs. The
defensible claim is narrower: compactscore exposed target alignment, and greedy
generation showed that target alignment does not yet transfer to stronger
pairwise judgment behavior.

## Scoring

Score both original dev and position-balanced dev with the default
`winner_only` mode for continuity with existing reports:

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

For target-alignment diagnostics, add:

```bash
--score-mode compact_structured_judgment
```

Do not treat compact structured scoring as the only success metric. It scores a
continuation containing gold target fields, so it is useful for checking whether
the LoRA learned the training target but can be optimistic relative to real
generation.

Then evaluate:

```bash
python scripts/evaluate_pairwise_scores.py \
  --dataset data/pairwise/reconcilebench_v0_1_dev_pairwise_posbalanced.jsonl \
  --scores r128_posbalanced=outputs/pairwise_scores/qwen3_8b_v0_1_dev_posbalanced_r128_posbalanced_compact.jsonl \
  --output-md reports/pairwise_v0_1_dev_posbalanced_r128_compact_eval.md \
  --output-json reports/pairwise_v0_1_dev_posbalanced_r128_compact_eval.json \
  --output-csv reports/pairwise_v0_1_dev_posbalanced_r128_compact_errors.csv
```
