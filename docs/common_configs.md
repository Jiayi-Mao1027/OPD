# Common Configs

This file records stable defaults for this project so future work does not
depend on chat context.

## Remote Workspace

```bash
HOST=10.26.128.46
PROJECT_ROOT=/data03/liang/mjy/reconcile_opsd
PY=/data/conda/envs/mjy/bin/python
MODEL_ROOT=/data/LLM
QWEN3_8B=/data/LLM/Qwen3-8B
```

Always start remote work from:

```bash
cd /data03/liang/mjy/reconcile_opsd
export PYTHONPATH=$PWD/src
```

## Conda And CUDA

Interactive shell:

```bash
source /data/conda/etc/profile.d/conda.sh
conda activate mjy
```

Non-interactive scripts can use the Python binary directly:

```bash
PY=/data/conda/envs/mjy/bin/python
```

CUDA extension environment:

```bash
export CUDA_HOME=/usr/local/cuda-12.2
export PATH=$CUDA_HOME/bin:/data/conda/envs/mjy/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}
```

Use `attn_implementation=eager` for first-stage Qwen3-8B runs. This avoids a
hard dependency on `flash-attn`, which is not currently reliable in the remote
environment.

## GPU Policy

The host exposes 4 H100 PCIe GPUs in the current session. No A100 devices were
visible during setup.

Before loading a model:

```bash
$PY scripts/gpu_status.py
eval "$($PY scripts/gpu_status.py --min-free-mb 20000 --max-used-mb 70000 --export)"
echo "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES"
```

Default small-model policy:

- require at least `20000 MB` free;
- avoid a GPU with more than `70000 MB` already used;
- log the chosen GPU before the run.

The user-level 70GB+ rule still matters for high-VRAM target experiments. For
8B QLoRA and constrained scoring, low VRAM use is expected and should be logged
as a small-model diagnostic run rather than treated as the final high-VRAM
experiment.

## First-Stage Model Defaults

Primary thinking-capable student:

```text
/data/LLM/Qwen3-8B
```

Current first-stage model constraints:

- Prefer Qwen3 instruct/chat models with thinking support.
- Prefer 8B or smaller.
- Do not use DeepSeek-R1-Distill/R1 in the first stage.
- Before using any ambiguous local model, inspect `config.json`,
  `tokenizer_config.json`, and render or generate a short chat-template smoke.

Template check:

```bash
$PY scripts/inspect_model_template.py \
  --model /data/LLM/Qwen3-8B \
  --enable-thinking \
  --output outputs/inspect/qwen3_8b_template.json
```

## Current Evaluation Defaults

The action-mode/REASON QLoRA line is frozen as a negative-result baseline.
Do not extend it with more steps until the target is redesigned.

Run constrained scoring:

```bash
eval "$($PY scripts/gpu_status.py --min-free-mb 20000 --max-used-mb 70000 --export)"

$PY scripts/score_action_modes.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/splits/reconcilebench_v0_dev.jsonl \
  --output outputs/scores/qwen3_8b_v0_dev_base_trainprompt_4bit.jsonl \
  --load-in-4bit \
  --prompt-style train \
  --candidate-set all \
  --attn-implementation eager
```

Adapter scoring:

```bash
eval "$($PY scripts/gpu_status.py --min-free-mb 20000 --max-used-mb 70000 --export)"

$PY scripts/score_action_modes.py \
  --model /data/LLM/Qwen3-8B \
  --adapter outputs/train_v0/qwen3_8b_action_lora_normreason_steps20/adapter \
  --dataset data/splits/reconcilebench_v0_dev.jsonl \
  --output outputs/scores/qwen3_8b_v0_dev_normreason_adapter_trainprompt_4bit.jsonl \
  --load-in-4bit \
  --prompt-style train \
  --candidate-set all \
  --attn-implementation eager
```

Report:

```bash
$PY scripts/compare_action_mode_runs.py \
  --dataset data/splits/reconcilebench_v0_dev.jsonl \
  --scores base=outputs/scores/qwen3_8b_v0_dev_base_trainprompt_4bit.jsonl \
  --scores normreason=outputs/scores/qwen3_8b_v0_dev_normreason_adapter_trainprompt_4bit.jsonl \
  --output-md reports/reconcile_v0_eval_base_vs_qlora.md \
  --output-csv reports/reconcile_v0_error_table.csv \
  --output-json reports/reconcile_v0_eval_base_vs_qlora.json
```

Terminal-only report:

```bash
$PY scripts/compare_action_mode_runs.py \
  --dataset data/splits/reconcilebench_v0_dev.jsonl \
  --scores base=outputs/scores/qwen3_8b_v0_dev_base_trainprompt_4bit.jsonl \
  --scores normreason=outputs/scores/qwen3_8b_v0_dev_normreason_adapter_trainprompt_4bit.jsonl \
  --exclude-continue-reasoning \
  --output-md reports/reconcile_v0_eval_terminal_only.md \
  --output-csv reports/reconcile_v0_error_table_terminal_only.csv \
  --output-json reports/reconcile_v0_eval_terminal_only.json
```

## Pairwise Data Defaults

Build pairwise train data from train only:

```bash
$PY scripts/build_pairwise_judgment_data.py \
  --dataset data/splits/reconcilebench_v0_train.jsonl \
  --forbid-source-dataset data/splits/reconcilebench_v0_dev.jsonl \
  --output data/pairwise/reconcilebench_v0_train_pairwise.jsonl \
  --manifest-output data/pairwise/reconcilebench_v0_train_pairwise_manifest.json \
  --split-name train \
  --max-pairs-per-example 2 \
  --seed 20260630
```

Build pairwise dev data for evaluation only:

```bash
$PY scripts/build_pairwise_judgment_data.py \
  --dataset data/splits/reconcilebench_v0_dev.jsonl \
  --forbid-source-dataset data/splits/reconcilebench_v0_train.jsonl \
  --output data/pairwise/reconcilebench_v0_dev_pairwise.jsonl \
  --manifest-output data/pairwise/reconcilebench_v0_dev_pairwise_manifest.json \
  --split-name dev \
  --max-pairs-per-example 2 \
  --seed 20260630
```

Current pairwise v0 draft:

- train: `76` pairs from `38` source examples;
- dev: `28` pairs from `14` source examples;
- both manifests have empty forbidden source-id and prompt-hash overlap.

Score pairwise dev before pairwise QLoRA:

```bash
eval "$($PY scripts/gpu_status.py --min-free-mb 20000 --max-used-mb 70000 --export)"

$PY scripts/score_pairwise_judgments.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/pairwise/reconcilebench_v0_dev_pairwise.jsonl \
  --output outputs/pairwise_scores/qwen3_8b_v0_dev_pairwise_base_4bit.jsonl \
  --load-in-4bit \
  --attn-implementation eager

$PY scripts/evaluate_pairwise_scores.py \
  --dataset data/pairwise/reconcilebench_v0_dev_pairwise.jsonl \
  --scores base=outputs/pairwise_scores/qwen3_8b_v0_dev_pairwise_base_4bit.jsonl \
  --output-md reports/pairwise_v0_dev_base_eval.md \
  --output-json reports/pairwise_v0_dev_base_eval.json \
  --output-csv reports/pairwise_v0_dev_base_errors.csv
```

Current pairwise dev base result:

- winner accuracy: `0.6786` over `28` pairs;
- `lost_fork_state`: `0/4`;
- `wrong_scope`: `1/4`;
- peak allocated CUDA memory: about `7217 MB`.

Next-stage pairwise plan:

- see `docs/pairwise_v0_1_plan.md`;
- repair `fork_state` and `scope_contract` before full QLoRA;
- re-score Qwen3-8B 4-bit base on pairwise v0.1 before training adapters.

## Proxy And GitHub

The server uses `mihomo` with local ports:

```text
HTTP proxy: 127.0.0.1:7890
SOCKS proxy: 127.0.0.1:7891
Controller: 127.0.0.1:9091
```

Set GitHub/network proxy:

```bash
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
export HTTP_PROXY=$http_proxy
export HTTPS_PROXY=$https_proxy
export no_proxy=localhost,127.0.0.1,::1
```

If GitHub returns `Could not resolve host` or TLS handshake failures, first
check whether `GLOBAL` is accidentally set to `DIRECT`:

```bash
python3 - <<'PY'
import json, urllib.request
data = json.load(urllib.request.urlopen("http://127.0.0.1:9091/proxies", timeout=5))
print(data["proxies"]["GLOBAL"].get("now"))
PY
```

Switch `GLOBAL` to the first non-`DIRECT` and non-`REJECT` choice:

```bash
python3 - <<'PY'
import json, urllib.parse, urllib.request
base = "http://127.0.0.1:9091"
proxies = json.load(urllib.request.urlopen(base + "/proxies", timeout=5))["proxies"]
choices = proxies["GLOBAL"].get("all") or []
choice = next(x for x in choices if x not in {"DIRECT", "REJECT"})
url = base + "/proxies/" + urllib.parse.quote("GLOBAL", safe="")
req = urllib.request.Request(
    url,
    data=json.dumps({"name": choice}).encode(),
    method="PUT",
    headers={"Content-Type": "application/json"},
)
urllib.request.urlopen(req, timeout=5).read()
print("GLOBAL -> non-direct choice")
PY
```

Then verify:

```bash
curl -I -L --proxy http://127.0.0.1:7890 https://github.com
git -c http.version=HTTP/1.1 ls-remote --heads origin
```

## Git Discipline

Before committing:

```bash
git status --short
$PY -m pytest
$PY -m compileall src scripts
rg -n "hf_|ghp_|password|passwd|secret" . -g '!outputs/**' -g '!**/__pycache__/**'
```

Do not commit:

- `.secrets/`;
- `.env*`;
- model weights or adapters;
- large generated outputs;
- raw secrets or browser/chat dumps.

Tracked reports should be small, summary-level artifacts under `reports/`.

## Pro Collaboration

Use ChatGPT Pro for research planning, contribution checks, and target-design
critique. For long work:

- wait for a single Pro answer to finish;
- switch to a fresh Pro chat only after several turns or when the chat context
  itself becomes long;
- when switching, restate the compact project background, current metrics,
  current blockers, and the exact question;
- do not send credentials, tokens, passwords, cookies, or private keys.
