# Data And Model Inventory

Initial survey date: 2026-06-30.

## Storage

- `/data03`: 17T total, 15T used, 1.5T available, 91% used.
- `/data`: 11T total, 9.3T used, 526G available, 95% used.
- `/data01`: 17T total, 6.6T used, 8.9T available, 43% used.
- `/data/LLM` is a symlink to `/data01/LLM`.

Disk space on `/data` is tight. Avoid copying model weights or large checkpoints into the project repo.

## Verified Candidate Models

Useful first-stage models found under `/data/LLM`:

- `/data/LLM/Qwen2.5-7B-Instruct`
- `/data/LLM/Qwen2.5-14B-Instruct`
- `/data/LLM/Qwen2.5-32B-Instruct`
- `/data/LLM/Qwen3-8B`
- `/data/LLM/Qwen3-30B-A3B`
- `/data/LLM/Qwen3-30B-A3B-Thinking`
- `/data/LLM/Qwen3-Next-80B-A3B-Thinking`
- `/data/LLM/Llama-3.1-8B-Instruct`
- `/data/LLM/Llama-3.3-70B-Instruct`
- `/data/LLM/YuFeng-XGuard-Reason-8B`
- `/data/LLM/Meta-SecAlign-8B`
- `/data/LLM/Meta-SecAlign-70B`
- `/data/LLM/Llama-Guard-3-1B`
- `/data/LLM/Llama-Guard-3-11B-Vision`
- `/data/LLM/PIGuard`

No `DeepSeek-R1-Distill-Qwen-*` directory was found in the initial scan.

## Thinking / Template Verification

Follow-up verification inspected `config.json`, `generation_config.json`, and `tokenizer_config.json` for the main candidates.

Observed model categories:

- Native thinking-template candidates:
  - `/data/LLM/Qwen3-8B`
  - `/data/LLM/Qwen3-30B-A3B`
  - `/data/LLM/Qwen3-30B-A3B-Thinking`
  - `/data/LLM/Qwen3-Next-80B-A3B-Thinking`
  - `/data/LLM/Qwen3.5-4B` has a long chat template mentioning thinking, but its architecture/usage needs extra verification before use.
- Ordinary instruct/chat baselines:
  - `/data/LLM/Qwen2.5-7B-Instruct`
  - `/data/LLM/Qwen2.5-14B-Instruct`
  - `/data/LLM/Qwen2.5-32B-Instruct`
  - `/data/LLM/Qwen3-4B-Instruct`
  - `/data/LLM/Llama-3.3-70B-Instruct`
- Safety-specialized or classifier-like candidates:
  - `/data/LLM/YuFeng-XGuard-Reason-8B` uses a safety-evaluation-oriented template; verify generation behavior before using it as a student model.
  - `/data/LLM/Meta-SecAlign-8B`
  - `/data/LLM/Meta-SecAlign-70B`

Working priority for method experiments:

1. `/data/LLM/Qwen3-8B` for smoke tests because it has a thinking-capable template and manageable size.
2. `/data/LLM/Qwen2.5-7B-Instruct` as a non-thinking instruct baseline.
3. `/data/LLM/Qwen3-30B-A3B-Thinking` only after the 8B/smaller pipeline is stable and the user approves a larger run.
4. `/data/LLM/Qwen3-Next-80B-A3B-Thinking` only after the pipeline is stable and large-model resources are intentionally scheduled.
5. `/data/LLM/Qwen2.5-32B-Instruct` or `/data/LLM/Llama-3.3-70B-Instruct` as later non-thinking large baselines, not first-stage targets.

Before using any model in an experiment, run a small template/render/generation smoke check and record:

- whether `chat_template` exists;
- whether the template includes thinking-specific controls or markers;
- whether generated output shows the expected thinking/action-mode structure;
- whether the prompt format matches training/evaluation data.

## Model Download Wishlist

The user has deferred R1-style experiments for the first stage. Do not request these downloads now unless the project direction changes.

Only needed later if the project decides to rely on R1-style distillation baselines:

- `DeepSeek-R1-Distill-Qwen-14B`
- `DeepSeek-R1-Distill-Qwen-32B`

Optional later:

- `DeepSeek-R1-Distill-Llama-70B`

## Environment

Conda:

- conda executable: `/data/conda/bin/conda`
- target env: `/data/conda/envs/mjy`
- Python: 3.11.0
- Torch: 2.6.0+cu124
- CUDA runtime: 12.4
- GPUs visible from Torch: 4 x NVIDIA H100 PCIe, about 79.1 GiB each

Installed packages in `mjy`:

- `transformers==4.57.1`
- `accelerate==1.13.0`
- `peft==0.18.1`
- `trl==0.29.1`
- `datasets==4.6.1`
- `vllm==0.8.5.post1`
- `sentencepiece==0.2.1`
- `safetensors==0.7.0`
- `tokenizers==0.22.2`
- `xformers==0.0.29.post2`

Missing packages relevant to planned experiments:

- `bitsandbytes`
- `deepspeed`
- `flash-attn`

## Initial GPU State

Initial survey showed all 4 GPUs occupied:

- GPU 0 H100 PCIe: about 75GB used by a vLLM process.
- GPU 1 H100 PCIe: about 40GB used by a Python process in `self_forcing`.
- GPU 2 H100 PCIe: about 62GB used by a Python process.
- GPU 3 H100 PCIe: about 75GB used by a Python process in `zby`.

Always rerun `nvidia-smi` before experiments.

## GPU Count Verification

Follow-up verification with `nvidia-smi -L`, GPU UUID/bus IDs, and `lspci` showed 4 visible NVIDIA H100 PCIe devices on `node-128-46`.

No A100 devices were visible on this machine during this check. If there are 2 A100 GPUs, they are likely on a different node or not exposed to this OS/session.
