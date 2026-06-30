# Project Status

Last updated: 2026-06-30 20:56 +08:00

## Current Objective

Create the initial project workspace for Reconcile-OPSD, turn the web-chat research idea into an actionable first-stage plan, and record the remote environment/model inventory.

## Git State

- Branch: `main`
- Initial commit: `b12406a docs: initialize reconcile opsd project`

## Current Location

- Remote project root: `/data03/liang/mjy/reconcile_opsd`
- Remote user confirmed: `root`
- Machine: `node-128-46`
- Conda env: `/data/conda/envs/mjy`
- Model root: `/data/LLM` -> `/data01/LLM`

## Done

- Read the open ChatGPT conversation titled `OPD safety research current state`.
- Extracted the main direction: Reconcile-OPSD / Fork-Preserving Judgment-Delta Self-Distillation.
- Confirmed the old `/data03/liang/mjy/safe_opd` directory already exists and should not be overwritten.
- Confirmed the `mjy` conda environment exists and can see 4 H100 PCIe GPUs.
- Confirmed several usable local models under `/data/LLM`.
- Created the initial Git repo and first commit.
- Rechecked GPU topology: `node-128-46` exposes 4 H100 PCIe devices; no A100 devices are visible from this OS/session.
- Inspected candidate chat templates and marked Qwen3 thinking-capable candidates as the first-priority student models.

## Current Blockers

- No GitHub remote URL has been configured yet.
- No DeepSeek-R1-Distill-Qwen model was found under `/data/LLM`.
- `mjy` currently lacks `bitsandbytes`, `deepspeed`, and `flash-attn`; this matters for QLoRA, multi-GPU training, and high-throughput long-context training.
- All 4 H100 GPUs had active processes during the initial survey, so no training should start without a fresh GPU check.
- Some local model names are ambiguous; every chosen model still needs a generation smoke test before training/evaluation.
- R1/DeepSeek-R1-Distill experiments are deferred for now.
- First-stage experiments should use 8B or smaller models where possible.

## Next Actions

- Ask ChatGPT Pro to investigate novelty/collision risks using the prepared context packet.
- Decide the first implementation target: data schema + action-mode labels, or baseline eval harness.
- Prefer `Qwen3-8B` for the first thinking-model smoke test; keep Qwen2.5 Instruct as a non-thinking baseline.
- Configure and push to GitHub repo `Jiayi-Mao1027/OPD`.
- Before high-VRAM runs, decide whether to install `bitsandbytes`, `deepspeed`, and `flash-attn` into `mjy`.
