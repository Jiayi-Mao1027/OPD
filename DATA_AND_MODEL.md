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

## Model Download Wishlist

Only needed if the project decides to rely on R1-style distillation baselines:

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

