# Reconcile-OPSD

This repository is the working space for an OPD safety research project.

Working thesis:

> Distill safety-relevant judgment improvements into reasoning models under conflicting or ambiguous scenarios, while preserving exploration, backtracking, uncertainty expression, and useful reasoning forks.

The project should not be framed as "safe OPD". The intended direction is:

- reconciliation ability rather than refusal-only safety;
- judgment-delta self-distillation rather than full CoT imitation;
- fork-preserving adaptive OPD rather than uniform reverse-KL pressure;
- action-mode distillation rather than copying teacher reasoning text.

## Roles

- Codex: engineering execution, remote setup, experiments, logs, Git hygiene.
- ChatGPT Pro: research planning, literature triage, contribution analysis, experimental critique.
- Git: shared factual state for progress, accepted decisions, plans, and experiment evidence.

## Remote

- Host: `10.26.128.46`
- Project root: `/data03/liang/mjy/reconcile_opsd`
- Conda environment: `mjy`
- Model root: `/data/LLM` -> `/data01/LLM`
- Existing related but separate old project: `/data03/liang/mjy/safe_opd`

Credentials are documented in the local private file `.secrets/PROJECT_CREDENTIALS.md`, which is intentionally not tracked by Git.

## First Runnable Loop

Use the small-model path first:

```bash
cd /data03/liang/mjy/reconcile_opsd
source /data/conda/etc/profile.d/conda.sh
conda activate mjy
export CUDA_HOME=/usr/local/cuda-12.2
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}
export PYTHONPATH=$PWD/src
```

Validate the seed data and utilities:

```bash
pytest -q
```

Check GPU state before loading a model:

```bash
python scripts/gpu_status.py
eval "$(python scripts/gpu_status.py --export)"
```

Audit the expanded v0 data and fixed split:

```bash
python scripts/audit_dataset.py \
  --dataset data/reconcilebench_v0.jsonl \
  --output outputs/audit/reconcilebench_v0_audit.json

python scripts/split_dataset.py \
  --dataset data/reconcilebench_v0.jsonl \
  --output-dir data/splits \
  --name reconcilebench_v0 \
  --dev-ratio 0.25 \
  --seed 20260630
```

Current ReconcileBench v0: `52` examples, all seven action modes covered. Fixed split: `38` train and `14` dev examples, with exactly two dev examples per action mode.

Inspect the Qwen3-8B chat template:

```bash
python scripts/inspect_model_template.py \
  --model /data/LLM/Qwen3-8B \
  --enable-thinking \
  --output outputs/inspect/qwen3_8b_template.json
```

Render a prompt without loading the model:

```bash
python scripts/smoke_generate.py \
  --model /data/LLM/Qwen3-8B \
  --enable-thinking \
  --render-only \
  --output outputs/smoke/qwen3_8b_render_only.json
```

Run a short generation only after checking GPU state:

```bash
CUDA_VISIBLE_DEVICES=1 python scripts/smoke_generate.py \
  --model /data/LLM/Qwen3-8B \
  --enable-thinking \
  --max-new-tokens 64 \
  --output outputs/smoke/qwen3_8b_generation.json
```

Run the seed action-mode baseline:

```bash
CUDA_VISIBLE_DEVICES=1 python scripts/generate_action_mode_predictions.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/reconcilebench_seed.jsonl \
  --output outputs/predictions/qwen3_8b_action_modes_seed.jsonl \
  --max-new-tokens 96 \
  --attn-implementation eager

python scripts/evaluate_baseline.py \
  --dataset data/reconcilebench_seed.jsonl \
  --predictions outputs/predictions/qwen3_8b_action_modes_seed.jsonl \
  --output outputs/eval/qwen3_8b_action_modes_seed_eval.json
```

Current seed baseline result: Qwen3-8B gets `0.1667` action-mode accuracy on 12 examples, mostly collapsing to `refuse` and `safe_high_level`.

Run a tiny QLoRA training smoke after checking GPU state:

```bash
CUDA_VISIBLE_DEVICES=1 python scripts/train_action_mode_lora.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/reconcilebench_seed.jsonl \
  --output-dir outputs/train_smoke/qwen3_8b_action_lora_steps2 \
  --limit 4 \
  --max-steps 2 \
  --max-length 768 \
  --attn-implementation eager
```

Current training smoke result: Qwen3-8B 4-bit QLoRA ran for 2 steps on 4 seed examples, saved an adapter under ignored `outputs/`, and used about `9355 MB` peak allocated CUDA memory.

Compare the smoke adapter against a quantized base-model control with the same training prompt:

```bash
CUDA_VISIBLE_DEVICES=1 python scripts/generate_action_mode_predictions.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/reconcilebench_seed.jsonl \
  --output outputs/predictions/qwen3_8b_action_modes_seed_trainprompt_4bit.jsonl \
  --max-new-tokens 96 \
  --attn-implementation eager \
  --load-in-4bit \
  --prompt-style train

CUDA_VISIBLE_DEVICES=1 python scripts/generate_action_mode_predictions.py \
  --model /data/LLM/Qwen3-8B \
  --adapter outputs/train_smoke/qwen3_8b_action_lora_steps2/adapter \
  --dataset data/reconcilebench_seed.jsonl \
  --output outputs/predictions/qwen3_8b_action_modes_seed_trainprompt_4bit_adapter_steps2.jsonl \
  --max-new-tokens 96 \
  --attn-implementation eager \
  --load-in-4bit \
  --prompt-style train
```

Current adapter eval result: both the 4-bit base control and the 2-step smoke adapter get `0.1667` action-mode accuracy on the 12 seed examples. The eval path is working; the tiny smoke adapter is not a quality improvement.

Labeling reference: `docs/action_mode_label_guide.md`.

Common remote paths, CUDA exports, GPU policy, proxy recovery, and GitHub push
checks are centralized in `docs/common_configs.md`.

Run a v0 train/dev QLoRA pass:

```bash
CUDA_VISIBLE_DEVICES=1 python scripts/train_action_mode_lora.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/splits/reconcilebench_v0_train.jsonl \
  --eval-dataset data/splits/reconcilebench_v0_dev.jsonl \
  --output-dir outputs/train_v0/qwen3_8b_action_lora_steps20 \
  --max-steps 20 \
  --max-length 768 \
  --eval-max-new-tokens 96 \
  --attn-implementation eager
```

Current v0 result: the 4-bit base control gets `0.4286` dev action-mode accuracy; the 20-step QLoRA adapter gets `0.3571`. This is a useful negative result: training runs and broadens predicted modes, but does not yet improve dev accuracy.

The trainer also supports a shorter target format:

```bash
CUDA_VISIBLE_DEVICES=1 python scripts/train_action_mode_lora.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/splits/reconcilebench_v0_train.jsonl \
  --eval-dataset data/splits/reconcilebench_v0_dev.jsonl \
  --output-dir outputs/train_v0/qwen3_8b_action_lora_normreason_steps20 \
  --max-steps 20 \
  --max-length 768 \
  --eval-max-new-tokens 96 \
  --attn-implementation eager \
  --target-style normalized_reason
```

Current normalized-target result: dev accuracy returns to `0.4286`, matching the 4-bit base control and avoiding most repetitive reason generation, but still not beating the base model.

The reproducible wrapper for the same path is:

```bash
TARGET_STYLE=normalized_reason MAX_STEPS=20 scripts/run_qwen3_v0_qlora.sh
```

## Current Direction After Pro Review

The v0 action-mode/REASON QLoRA line is now frozen as a negative-result
baseline. Do not continue it with more steps until the target is redesigned.

The next diagnostic loop is constrained scoring and audit:

```bash
eval "$(python scripts/gpu_status.py --export)"

python scripts/score_action_modes.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/splits/reconcilebench_v0_dev.jsonl \
  --output outputs/scores/qwen3_8b_v0_dev_base_trainprompt_4bit.jsonl \
  --load-in-4bit \
  --prompt-style train \
  --candidate-set all \
  --attn-implementation eager
```

Score the normalized-reason adapter the same way:

```bash
eval "$(python scripts/gpu_status.py --export)"

python scripts/score_action_modes.py \
  --model /data/LLM/Qwen3-8B \
  --adapter outputs/train_v0/qwen3_8b_action_lora_normreason_steps20/adapter \
  --dataset data/splits/reconcilebench_v0_dev.jsonl \
  --output outputs/scores/qwen3_8b_v0_dev_normreason_adapter_trainprompt_4bit.jsonl \
  --load-in-4bit \
  --prompt-style train \
  --candidate-set all \
  --attn-implementation eager
```

Generate the combined report:

```bash
python scripts/compare_action_mode_runs.py \
  --dataset data/splits/reconcilebench_v0_dev.jsonl \
  --scores base=outputs/scores/qwen3_8b_v0_dev_base_trainprompt_4bit.jsonl \
  --scores normreason=outputs/scores/qwen3_8b_v0_dev_normreason_adapter_trainprompt_4bit.jsonl \
  --output-md reports/reconcile_v0_eval_base_vs_qlora.md \
  --output-csv reports/reconcile_v0_error_table.csv \
  --output-json reports/reconcile_v0_eval_base_vs_qlora.json
```

Use `--exclude-continue-reasoning` when reporting terminal response actions
only. `continue_reasoning` is being moved to a separate prefix-level fork-state
target.

Current constrained-scoring result on v0 dev:

- all-mode accuracy: base `0.4286`, normalized adapter `0.4286`;
- macro-F1: base `0.2880`, normalized adapter `0.3293`;
- top-2 allowed accuracy: base `0.5714`, normalized adapter `0.7143`;
- terminal-only accuracy after excluding `continue_reasoning` gold items:
  base `0.5000`, normalized adapter `0.5000`.
