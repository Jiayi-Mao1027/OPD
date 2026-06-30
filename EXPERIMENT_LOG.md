# Experiment Log

No experiments have been run in this repository yet.

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
