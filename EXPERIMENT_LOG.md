# Experiment Log

This log records environment checks, runnable smokes, baselines, and evaluation evidence.

## 2026-06-30 20:56 +08:00 - Initial Environment Survey

Commit: `b12406a docs: initialize reconcile opsd project`
Branch: `main`
Machine: `node-128-46`
Project path: `/data03/liang/mjy/reconcile_opsd`
Conda env: `/data/conda/envs/mjy`

Commands summarized:

```bash
nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits
/data/conda/bin/conda run -n mjy python -V
/data/conda/bin/conda run -n mjy python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.device_count())"
find -L /data/LLM -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | sort
```

GPU before:

```text
GPU 0: NVIDIA H100 PCIe, 81559 MiB total, about 75315 MiB used
GPU 1: NVIDIA H100 PCIe, 81559 MiB total, about 40173 MiB used
GPU 2: NVIDIA H100 PCIe, 81559 MiB total, about 61823 MiB used
GPU 3: NVIDIA H100 PCIe, 81559 MiB total, about 75447 MiB used
```

Result:

- Environment is usable for planning.
- Do not start training until a fresh GPU availability check is done.
- The target `mjy` environment has core training packages but lacks `bitsandbytes`, `deepspeed`, and `flash-attn`.

Next step:

- Prepare Pro literature/context packet and choose first smoke experiment after planning.

## 2026-06-30 21:33 +08:00 - Remote GitHub And Dependency Setup

Commit before action: `44a66b3 docs: scope first stage to small thinking models`
Branch: `main`
Machine: `node-128-46`
Project path: `/data03/liang/mjy/reconcile_opsd`
Conda env: `/data/conda/envs/mjy`

Actions:

- Configured clean GitHub remote URL: `https://github.com/Jiayi-Mao1027/OPD.git`.
- Found local server proxy at `127.0.0.1:7890/7891`.
- Pushed `main` to GitHub using the local proxy.
- Installed `bitsandbytes==0.49.2`.
- Installed `deepspeed==0.19.2`.
- Built `flash-attn==2.8.3.post1`, but import failed with a C++ ABI symbol error.
- Rebuild with `FLASH_ATTENTION_FORCE_CXX11_ABI=FALSE` timed out and left `flash-attn` unavailable.
- Restored `packaging==25.0` after a transient upgrade conflicted with mlflow packages.

Environment notes:

```bash
export CUDA_HOME=/usr/local/cuda-12.2
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}
```

Without those CUDA exports, deepspeed import can fail because the default shell does not expose `nvcc`.

Result:

- GitHub push succeeded.
- `bitsandbytes` import succeeded.
- `deepspeed` import succeeded with `CUDA_HOME=/usr/local/cuda-12.2`.
- `flash-attn` is not currently usable; first-stage scripts use eager attention.

## 2026-06-30 22:00 +08:00 - First Runnable Skeleton Smoke

Commit before action: `da51825 docs: record github push and dependency setup`
Branch: `main`
Machine: `node-128-46`
Project path: `/data03/liang/mjy/reconcile_opsd`
Conda env: `/data/conda/envs/mjy`
Model path: `/data/LLM/Qwen3-8B`

Checks:

```bash
pytest -q
python scripts/inspect_model_template.py --model /data/LLM/Qwen3-8B --enable-thinking
python scripts/smoke_generate.py --model /data/LLM/Qwen3-8B --enable-thinking --max-new-tokens 64 --attn-implementation eager
```

Result:

- Unit tests passed: `6 passed`.
- Qwen3-8B template has `chat_template`, mentions thinking, and rendered successfully.
- Short generation succeeded on `CUDA_VISIBLE_DEVICES=1`.
- Output began with `<think>`, confirming thinking-style generation.
- Peak allocated memory for the smoke generation was about `15673 MB`.

## 2026-06-30 22:06 +08:00 - Qwen3-8B Seed Action-Mode Baseline

Commit before action: `673c91b code: add seed reconcilebench and smoke harness` plus the action-mode runner working-tree changes committed in the next project commit.
Branch: `main`
Machine: `node-128-46`
Project path: `/data03/liang/mjy/reconcile_opsd`
Conda env: `/data/conda/envs/mjy`
Model path: `/data/LLM/Qwen3-8B`
Dataset: `data/reconcilebench_seed.jsonl`

Command:

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

GPU:

```text
Used CUDA_VISIBLE_DEVICES=1.
Peak allocated memory: about 15692 MB.
```

Result:

```text
total = 12
action_mode_accuracy = 0.1667
predicted_counts = refuse: 6, safe_high_level: 5, direct_answer: 1
expected_counts = safe_redirect: 3, partial_allowed: 2, ask_clarification: 2, safe_high_level: 2, continue_reasoning: 2, direct_answer: 1
```

Interpretation:

- The base Qwen3-8B model produces valid explicit action-mode labels when thinking trace is disabled.
- It strongly collapses toward `refuse` and `safe_high_level`.
- It fails the intended reconciliation taxonomy on ambiguous, partial-allowed, safe-redirect, and evidence-calibration examples.
- This is a useful first baseline for motivating judgment-delta and fork-preserving training.

## 2026-06-30 22:13 +08:00 - Qwen3-8B Action-Mode QLoRA Training Smoke

Commit before action: `745cb9d code: add qwen action-mode baseline runner`
Branch: `main`
Machine: `node-128-46`
Project path: `/data03/liang/mjy/reconcile_opsd`
Conda env: `/data/conda/envs/mjy`
Model path: `/data/LLM/Qwen3-8B`
Dataset: `data/reconcilebench_seed.jsonl`

Command:

```bash
CUDA_VISIBLE_DEVICES=1 timeout 600 python scripts/train_action_mode_lora.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/reconcilebench_seed.jsonl \
  --output-dir outputs/train_smoke/qwen3_8b_action_lora_steps2 \
  --limit 4 \
  --max-steps 2 \
  --max-length 768 \
  --attn-implementation eager
```

Result:

```text
num_examples = 4
max_steps = 2
losses = 5.6548, 3.3280
load_in_4bit = true
cuda_max_memory_allocated_mb = 9354.79
adapter = outputs/train_smoke/qwen3_8b_action_lora_steps2/adapter
```

Interpretation:

- The current environment can load Qwen3-8B in 4-bit, attach LoRA adapters, train, and save an adapter.
- The smoke used only 4 examples and 2 optimizer steps; the loss drop is a plumbing signal, not a quality claim.
- Next verification should load the saved adapter and run the same action-mode eval path before scaling data or steps.

## 2026-06-30 22:28 +08:00 - Qwen3-8B Smoke Adapter Eval

Commit before action: `5bbfb7e code: add qlora action-mode training smoke`
Branch: `main`
Machine: `node-128-46`
Project path: `/data03/liang/mjy/reconcile_opsd`
Conda env: `/data/conda/envs/mjy`
Model path: `/data/LLM/Qwen3-8B`
Adapter path: `outputs/train_smoke/qwen3_8b_action_lora_steps2/adapter`
Dataset: `data/reconcilebench_seed.jsonl`

Adapter metadata:

```text
base_model_name_or_path = /data/LLM/Qwen3-8B
r = 8
lora_alpha = 16
target_modules = o_proj, gate_proj, v_proj, q_proj, up_proj, k_proj, down_proj
```

Commands:

```bash
CUDA_VISIBLE_DEVICES=1 python scripts/generate_action_mode_predictions.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/reconcilebench_seed.jsonl \
  --output outputs/predictions/qwen3_8b_action_modes_seed_trainprompt_4bit.jsonl \
  --max-new-tokens 96 \
  --attn-implementation eager \
  --load-in-4bit \
  --prompt-style train

python scripts/evaluate_baseline.py \
  --dataset data/reconcilebench_seed.jsonl \
  --predictions outputs/predictions/qwen3_8b_action_modes_seed_trainprompt_4bit.jsonl \
  --output outputs/eval/qwen3_8b_action_modes_seed_trainprompt_4bit_eval.json

CUDA_VISIBLE_DEVICES=1 python scripts/generate_action_mode_predictions.py \
  --model /data/LLM/Qwen3-8B \
  --adapter outputs/train_smoke/qwen3_8b_action_lora_steps2/adapter \
  --dataset data/reconcilebench_seed.jsonl \
  --output outputs/predictions/qwen3_8b_action_modes_seed_trainprompt_4bit_adapter_steps2.jsonl \
  --max-new-tokens 96 \
  --attn-implementation eager \
  --load-in-4bit \
  --prompt-style train

python scripts/evaluate_baseline.py \
  --dataset data/reconcilebench_seed.jsonl \
  --predictions outputs/predictions/qwen3_8b_action_modes_seed_trainprompt_4bit_adapter_steps2.jsonl \
  --output outputs/eval/qwen3_8b_action_modes_seed_trainprompt_4bit_adapter_steps2_eval.json
```

Result:

```text
base_4bit_trainprompt:
  total = 12
  action_mode_accuracy = 0.1667
  predicted_counts = refuse: 2, safe_high_level: 8, direct_answer: 1, safe_redirect: 1

adapter_steps2_4bit_trainprompt:
  total = 12
  action_mode_accuracy = 0.1667
  predicted_counts = refuse: 2, safe_high_level: 7, direct_answer: 2, safe_redirect: 1
```

Verification:

- `pytest -q`: `7 passed`.
- The adapter config points back to `/data/LLM/Qwen3-8B`.
- Prediction records now include adapter base path, 4-bit flag, prompt style, requested thinking flag, template thinking support, and input device metadata.

Interpretation:

- The adapter-aware eval path works and is comparable against a 4-bit base control.
- The 2-step smoke adapter does not improve seed action-mode accuracy.
- The next scaling step should wait until the dataset has a fixed train/dev split and the action-mode taxonomy is less ambiguous.

## 2026-06-30 22:41 +08:00 - ReconcileBench v0 Dataset And Split

Commit before action: `edb2914 code: add adapter-aware action eval`
Branch: `main`
Machine: local Windows mirror, then synced to `node-128-46`

Actions:

- Added dataset audit utilities in `src/reconcile_opsd/dataset_tools.py`.
- Added CLI wrappers: `scripts/audit_dataset.py` and `scripts/split_dataset.py`.
- Added three draft data batches under `data/drafts/`.
- Built `data/reconcilebench_v0.jsonl` from the 12 seed examples plus 40 new draft examples.
- Created fixed split files under `data/splits/`.

Verification:

```bash
pytest -q
python scripts/audit_dataset.py --dataset data/reconcilebench_v0.jsonl --output outputs/audit/reconcilebench_v0_audit.json
python scripts/split_dataset.py --dataset data/reconcilebench_v0.jsonl --output-dir data/splits --name reconcilebench_v0 --dev-ratio 0.25 --seed 20260630
```

Result:

```text
full dataset:
  total = 52
  duplicate_ids = none
  action_mode_counts =
    ask_clarification: 8
    continue_reasoning: 9
    direct_answer: 7
    partial_allowed: 7
    refuse: 7
    safe_high_level: 7
    safe_redirect: 7
  scenario_type_counts =
    ambiguous_intent: 5
    benign_sensitive: 17
    clear_harmful: 8
    dual_use: 6
    long_context_distraction: 7
    non_safety_uncertainty: 9

split:
  train = 38
  dev = 14
  dev action_mode_counts = 2 examples for each of the 7 action modes
```

Interpretation:

- The project now has a small but usable v0 dataset with explicit `refuse` coverage and a fixed dev split.
- The data is still synthetic/seed-quality and should be treated as a scaffold for method iteration, not as a publishable benchmark.
- The next training run can use `data/splits/reconcilebench_v0_train.jsonl` and evaluate on `data/splits/reconcilebench_v0_dev.jsonl`.

## 2026-06-30 22:54 +08:00 - Qwen3-8B v0 QLoRA 20-Step Run

Commit before action: `e8384aa data: add reconcilebench v0 split`
Branch: `main`
Machine: `node-128-46`
Project path: `/data03/liang/mjy/reconcile_opsd`
Conda env: `/data/conda/envs/mjy`
Model path: `/data/LLM/Qwen3-8B`
Train dataset: `data/splits/reconcilebench_v0_train.jsonl`
Dev dataset: `data/splits/reconcilebench_v0_dev.jsonl`

Commands:

```bash
CUDA_VISIBLE_DEVICES=1 python scripts/generate_action_mode_predictions.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/splits/reconcilebench_v0_dev.jsonl \
  --output outputs/predictions/qwen3_8b_action_modes_v0_dev_trainprompt_4bit.jsonl \
  --max-new-tokens 96 \
  --attn-implementation eager \
  --load-in-4bit \
  --prompt-style train

python scripts/evaluate_baseline.py \
  --dataset data/splits/reconcilebench_v0_dev.jsonl \
  --predictions outputs/predictions/qwen3_8b_action_modes_v0_dev_trainprompt_4bit.jsonl \
  --output outputs/eval/qwen3_8b_action_modes_v0_dev_trainprompt_4bit_eval.json

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

Result:

```text
4-bit base dev control:
  total = 14
  action_mode_accuracy = 0.4286
  predicted_counts = safe_high_level: 7, refuse: 5, direct_answer: 2

20-step QLoRA adapter:
  total = 14
  action_mode_accuracy = 0.3571
  predicted_counts = safe_high_level: 4, ask_clarification: 3, safe_redirect: 4, direct_answer: 2, refuse: 1
  train loss first -> last = 5.9287 -> 1.7881
  peak allocated CUDA memory = 9354.79 MB
```

Interpretation:

- The v0 train/dev loop works end to end: train, save adapter, generate dev predictions, and write eval metrics.
- The adapter predicts a broader label distribution than the base control, but dev accuracy is lower.
- Several dev generations show repetitive reason text, so longer training without fixing target formatting/data quality is not justified yet.
- Next step should be research/design review: likely improve labels, target format, response-level evaluation, and maybe train on shorter normalized reasons rather than raw `judgment_delta`.

## 2026-06-30 23:03 +08:00 - Qwen3-8B v0 QLoRA Normalized-Reason Target

Commit before action: `46d8406 exp: log qwen3 v0 qlora result`
Branch: `main`
Machine: `node-128-46`
Project path: `/data03/liang/mjy/reconcile_opsd`
Conda env: `/data/conda/envs/mjy`
Model path: `/data/LLM/Qwen3-8B`
Train dataset: `data/splits/reconcilebench_v0_train.jsonl`
Dev dataset: `data/splits/reconcilebench_v0_dev.jsonl`

Change:

- Added `--target-style normalized_reason` to `scripts/train_action_mode_lora.py`.
- This replaces heterogeneous `judgment_delta` text with a fixed short reason per action mode.
- Default remains `--target-style judgment_delta` for reproducibility of prior runs.

Command:

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

Result:

```text
4-bit base dev control:
  action_mode_accuracy = 0.4286
  predicted_counts = safe_high_level: 7, refuse: 5, direct_answer: 2

20-step QLoRA, judgment_delta target:
  action_mode_accuracy = 0.3571
  predicted_counts = safe_high_level: 4, ask_clarification: 3, safe_redirect: 4, direct_answer: 2, refuse: 1

20-step QLoRA, normalized_reason target:
  action_mode_accuracy = 0.4286
  predicted_counts = partial_allowed: 3, safe_redirect: 6, direct_answer: 4, refuse: 1
  train loss first -> last = 3.2749 -> 0.5582
  peak allocated CUDA memory = 9354.79 MB
```

Interpretation:

- Normalized reasons stabilize generation and remove most repeated `REASON` text.
- The normalized-target adapter recovers from the judgment-delta degradation, but only ties the base control.
- It still misses `ask_clarification` and `continue_reasoning` on dev, often mapping them to `safe_redirect` or `partial_allowed`.
- Next improvement should not be more steps alone; add response-level eval and/or a clearer classification-style target for clarification and fork-preservation behavior.

## 2026-06-30 23:58 +08:00 - Pro Review Follow-Up: Constrained Action-Mode Scoring

Commit before action: `e7cacd6 chore: add gpu run helpers`
Branch: `main`
Machine: `node-128-46`
Project path: `/data03/liang/mjy/reconcile_opsd`
Conda env: `/data/conda/envs/mjy`
Model path: `/data/LLM/Qwen3-8B`
Dev dataset: `data/splits/reconcilebench_v0_dev.jsonl`

Motivation:

- Two ChatGPT Pro reviews agreed that the current action-mode/REASON QLoRA line
  should be frozen as a negative-result baseline.
- The next diagnostic step is constrained scoring and audit, not more training
  steps on the same target.

GPU state before run:

```json
{
  "selected_gpu": 1,
  "name": "NVIDIA H100 PCIe",
  "memory_used_mb": 33257,
  "memory_free_mb": 47738,
  "utilization_gpu_pct": 86
}
```

Commands:

```bash
eval "$(python scripts/gpu_status.py --min-free-mb 20000 --max-used-mb 70000 --export)"

python scripts/score_action_modes.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/splits/reconcilebench_v0_dev.jsonl \
  --output outputs/scores/qwen3_8b_v0_dev_base_trainprompt_4bit.jsonl \
  --load-in-4bit \
  --prompt-style train \
  --candidate-set all \
  --attn-implementation eager

python scripts/score_action_modes.py \
  --model /data/LLM/Qwen3-8B \
  --adapter outputs/train_v0/qwen3_8b_action_lora_normreason_steps20/adapter \
  --dataset data/splits/reconcilebench_v0_dev.jsonl \
  --output outputs/scores/qwen3_8b_v0_dev_normreason_adapter_trainprompt_4bit.jsonl \
  --load-in-4bit \
  --prompt-style train \
  --candidate-set all \
  --attn-implementation eager

python scripts/compare_action_mode_runs.py \
  --dataset data/splits/reconcilebench_v0_dev.jsonl \
  --scores base=outputs/scores/qwen3_8b_v0_dev_base_trainprompt_4bit.jsonl \
  --scores normreason=outputs/scores/qwen3_8b_v0_dev_normreason_adapter_trainprompt_4bit.jsonl \
  --output-md reports/reconcile_v0_eval_base_vs_qlora.md \
  --output-csv reports/reconcile_v0_error_table.csv \
  --output-json reports/reconcile_v0_eval_base_vs_qlora.json
```

Result:

```text
All-mode constrained scoring, 14 dev examples:
  base acc = 0.4286
  base macro-F1 = 0.2880
  base top-2 allowed = 0.5714
  base average gold margin = -0.1497

  normalized adapter acc = 0.4286
  normalized adapter macro-F1 = 0.3293
  normalized adapter top-2 allowed = 0.7143
  normalized adapter average gold margin = -0.0012

Terminal-only report, excluding continue_reasoning gold items:
  base acc = 0.5000
  base macro-F1 = 0.3741
  normalized adapter acc = 0.5000
  normalized adapter macro-F1 = 0.4222

Peak allocated CUDA memory:
  base scoring = 7216.79 MB
  normalized adapter scoring = 7216.79 MB
```

Main error clusters:

- Base: `missing_clarification` 2, `wrong_scope` 2, `lost_continue_reasoning` 2.
- Normalized adapter: `missing_clarification` 2, `lost_continue_reasoning` 2,
  `terminal_mode_confusion` 2, `spurious_continue_reasoning` 1.

Interpretation:

- Constrained scoring confirms the same top-line accuracy as generation eval,
  but provides more useful diagnostics.
- The normalized adapter improves top-2 coverage and macro-F1 without improving
  top-1 accuracy.
- `ask_clarification` remains the clearest terminal-action weakness.
- `continue_reasoning` behaves like a fork-state/control target and should be
  split out rather than treated as a final user-visible action.
- Next step: audit the error table, then build pairwise judgment-delta examples
  from the clean/confusable cases.
