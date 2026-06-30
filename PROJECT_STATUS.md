# Project Status

Last updated: 2026-06-30 21:33 +08:00

## Current Objective

Create the initial project workspace for Reconcile-OPSD, turn the web-chat research idea into an actionable first-stage plan, and record the remote environment/model inventory.

## Git State

- Branch: `main`
- Initial commit: `b12406a docs: initialize reconcile opsd project`
- GitHub remote: `https://github.com/Jiayi-Mao1027/OPD.git`
- Latest pushed branch: `main`

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
- Configured GitHub remote and pushed `main` to `Jiayi-Mao1027/OPD`.
- Found the server proxy at `127.0.0.1:7890/7891` and used it for GitHub push.
- Installed `bitsandbytes==0.49.2` and `deepspeed==0.19.2` in `mjy`.
- Attempted `flash-attn`; it is currently unavailable because the first build had an ABI import error and the ABI-forced rebuild timed out.
- Verified `deepspeed` imports when `CUDA_HOME=/usr/local/cuda-12.2` is set.
- Added runnable package skeleton, seed ReconcileBench data, template inspection, smoke generation, and action-mode baseline scripts.
- Verified `pytest -q`: `7 passed`.
- Ran Qwen3-8B seed action-mode baseline: `12` examples, `0.1667` accuracy, with predictions collapsing toward `refuse` and `safe_high_level`.

## Current Blockers

- No DeepSeek-R1-Distill-Qwen model was found under `/data/LLM`.
- All 4 H100 GPUs had active processes during the initial survey, so no training should start without a fresh GPU check.
- Some local model names are ambiguous; every chosen model still needs a generation smoke test before training/evaluation.
- R1/DeepSeek-R1-Distill experiments are deferred for now.
- First-stage experiments should use 8B or smaller models where possible.
- Deepspeed/flash-attn workflows must set `CUDA_HOME=/usr/local/cuda-12.2`.
- First-stage Qwen3-8B scripts use `attn_implementation=eager` and do not require `flash-attn`.

## Next Actions

- Ask ChatGPT Pro to investigate novelty/collision risks using the prepared context packet.
- Decide the first implementation target: data schema + action-mode labels, or baseline eval harness.
- Prefer `Qwen3-8B` for the first thinking-model smoke test; keep Qwen2.5 Instruct as a non-thinking baseline.
- Run a template/generation smoke check for `Qwen3-8B`.
- Start implementing the dataset schema and baseline evaluation harness.
- Expand ReconcileBench beyond the 12 seed examples.
- Use the baseline failure pattern to design judgment-delta/action-mode training data.
