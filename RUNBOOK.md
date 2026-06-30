# Runbook

## Connect

Use SSH to connect to `10.26.128.46`. The working project directory is:

```bash
cd /data03/liang/mjy/reconcile_opsd
```

Use the conda environment:

```bash
/data/conda/bin/conda run -n mjy python -V
```

For interactive shell sessions:

```bash
source /data/conda/etc/profile.d/conda.sh
conda activate mjy
```

CUDA extension environment:

```bash
export CUDA_HOME=/usr/local/cuda-12.2
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}
```

Use those exports before deepspeed or flash-attn related runs.

Common defaults for paths, CUDA, GPU policy, Qwen3-8B evaluation, proxy
recovery, and GitHub checks are also recorded in `docs/common_configs.md`.

Server proxy for GitHub/network operations:

```bash
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
export HTTP_PROXY=$http_proxy
export HTTPS_PROXY=$https_proxy
export no_proxy=localhost,127.0.0.1,::1
```

## Standard Checks

Git:

```bash
git status --short --branch
git log --oneline -5
```

GPU:

```bash
nvidia-smi
nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu --format=csv
nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_memory --format=csv
python scripts/gpu_status.py
python scripts/gpu_status.py --export
```

The project GPU helper selects a device with at least `20000 MB` free and at most
`70000 MB` already used by default. Override with `--min-free-mb` and
`--max-used-mb` only when the reason is logged.

Models:

```bash
find -L /data/LLM -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | sort
```

Model template check:

```bash
python3 - <<'PY'
import json, pathlib, re
model = pathlib.Path("/data/LLM/Qwen3-8B")
tok = json.loads((model / "tokenizer_config.json").read_text(errors="replace"))
cfg = json.loads((model / "config.json").read_text(errors="replace"))
tmpl = tok.get("chat_template") or ""
print("model_type:", cfg.get("model_type"))
print("architectures:", cfg.get("architectures"))
print("has_chat_template:", bool(tmpl))
print("template_mentions_thinking:", bool(re.search(r"think|reason|thinking|enable_thinking", tmpl, re.I)))
print("template_preview:", " ".join(tmpl.split())[:500])
PY
```

Environment packages:

```bash
/data/conda/bin/conda run -n mjy python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.device_count())"
```

Installed training dependencies:

```bash
source /data/conda/etc/profile.d/conda.sh
conda activate mjy
export CUDA_HOME=/usr/local/cuda-12.2
export PATH=$CUDA_HOME/bin:$PATH
python - <<'PY'
import importlib.metadata as md
for p in ["bitsandbytes", "deepspeed", "flash-attn", "packaging"]:
    try:
        print(f"{p}=={md.version(p)}")
    except md.PackageNotFoundError:
        print(f"{p}=MISSING")
PY
```

## Logging Required For Experiments

Before an experiment, add an `EXPERIMENT_LOG.md` entry with:

- date/time;
- Git commit;
- branch;
- model path;
- dataset/input;
- command;
- expected GPU memory;
- GPU state before run.

After an experiment, update the entry with:

- actual peak memory;
- GPU state during/after;
- result metrics;
- failure reason if any;
- next action.

## 70GB+ Rule

High-VRAM target experiments must exceed 70GB actual GPU memory usage. If they do not:

1. Check whether the intended model was actually loaded.
2. Check precision and quantization.
3. Check tensor parallel / device map.
4. Check sequence length and micro batch size.
5. Check whether gradient checkpointing, LoRA, or CPU offload changed memory usage.
6. Mark the result as suspect until explained.

For first-stage 8B QLoRA runs, use the inverse safety rule: avoid devices that
already have more than `70000 MB` used, and log the selected device before
starting. The helper script enforces this default policy.

## Standard v0 QLoRA Runner

Use this wrapper for reproducible Qwen3-8B v0 action-mode runs:

```bash
TARGET_STYLE=normalized_reason MAX_STEPS=20 scripts/run_qwen3_v0_qlora.sh
```

Common overrides:

```bash
TARGET_STYLE=judgment_delta OUTPUT_DIR=outputs/train_v0/qwen3_8b_action_lora_steps20 scripts/run_qwen3_v0_qlora.sh
MIN_FREE_MB=20000 MAX_USED_MB=70000 scripts/run_qwen3_v0_qlora.sh
```

Current reference configs:

```text
configs/qwen3_8b_v0_judgment_delta_steps20.json
configs/qwen3_8b_v0_normalized_reason_steps20.json
```

## Constrained Scoring And Audit

Use this path after the current v0 action-mode/REASON SFT negative results.
It scores candidate labels directly instead of asking the model to generate a
free-form `ACTION_MODE + REASON` response.

Base control:

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

Normalized-reason adapter:

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

Combined report:

```bash
python scripts/compare_action_mode_runs.py \
  --dataset data/splits/reconcilebench_v0_dev.jsonl \
  --scores base=outputs/scores/qwen3_8b_v0_dev_base_trainprompt_4bit.jsonl \
  --scores normreason=outputs/scores/qwen3_8b_v0_dev_normreason_adapter_trainprompt_4bit.jsonl \
  --output-md reports/reconcile_v0_eval_base_vs_qlora.md \
  --output-csv reports/reconcile_v0_error_table.csv \
  --output-json reports/reconcile_v0_eval_base_vs_qlora.json
```

Terminal-action-only report:

```bash
python scripts/compare_action_mode_runs.py \
  --dataset data/splits/reconcilebench_v0_dev.jsonl \
  --scores base=outputs/scores/qwen3_8b_v0_dev_base_trainprompt_4bit.jsonl \
  --scores normreason=outputs/scores/qwen3_8b_v0_dev_normreason_adapter_trainprompt_4bit.jsonl \
  --exclude-continue-reasoning \
  --output-md reports/reconcile_v0_eval_terminal_only.md \
  --output-csv reports/reconcile_v0_error_table_terminal_only.csv
```

## Pairwise Judgment-Delta Data

Build train pairs only from the train split and forbid the dev split:

```bash
python scripts/build_pairwise_judgment_data.py \
  --dataset data/splits/reconcilebench_v0_train.jsonl \
  --forbid-source-dataset data/splits/reconcilebench_v0_dev.jsonl \
  --output data/pairwise/reconcilebench_v0_train_pairwise.jsonl \
  --manifest-output data/pairwise/reconcilebench_v0_train_pairwise_manifest.json \
  --split-name train \
  --max-pairs-per-example 2 \
  --seed 20260630
```

Build dev pairs separately for pairwise evaluation:

```bash
python scripts/build_pairwise_judgment_data.py \
  --dataset data/splits/reconcilebench_v0_dev.jsonl \
  --forbid-source-dataset data/splits/reconcilebench_v0_train.jsonl \
  --output data/pairwise/reconcilebench_v0_dev_pairwise.jsonl \
  --manifest-output data/pairwise/reconcilebench_v0_dev_pairwise_manifest.json \
  --split-name dev \
  --max-pairs-per-example 2 \
  --seed 20260630
```

Do not merge dev pairwise data into training. The builder checks source-id and
prompt-hash overlap against the forbidden split.

Pairwise base scoring:

```bash
eval "$(python scripts/gpu_status.py --export)"
python scripts/score_pairwise_judgments.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/pairwise/reconcilebench_v0_dev_pairwise.jsonl \
  --output outputs/pairwise_scores/qwen3_8b_v0_dev_pairwise_base_4bit.jsonl \
  --load-in-4bit \
  --attn-implementation eager

python scripts/evaluate_pairwise_scores.py \
  --dataset data/pairwise/reconcilebench_v0_dev_pairwise.jsonl \
  --scores base=outputs/pairwise_scores/qwen3_8b_v0_dev_pairwise_base_4bit.jsonl \
  --output-md reports/pairwise_v0_dev_base_eval.md \
  --output-json reports/pairwise_v0_dev_base_eval.json \
  --output-csv reports/pairwise_v0_dev_base_errors.csv
```

Next pairwise stage:

- Follow `docs/pairwise_v0_1_plan.md`.
- Do not run full pairwise QLoRA before v0.1 fork-state and scope-contract
  fields are inspectable and the Qwen3-8B 4-bit base has been re-scored.
