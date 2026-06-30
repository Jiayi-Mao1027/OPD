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
```

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
