# Project Status

Last updated: 2026-06-30 20:56 +08:00

## Current Objective

Create the initial project workspace for Reconcile-OPSD, turn the web-chat research idea into an actionable first-stage plan, and record the remote environment/model inventory.

## Current Location

- Remote project root: `/data03/liang/mjy/reconcile_opsd`
- Remote user confirmed: `root`
- Machine: `node-128-46`
- Conda env: `/data/conda/envs/mjy`
- Model root: `/data/LLM` -> `/data01/LLM`

## Done

- Read the open ChatGPT conversation titled `OPD安全研究现状`.
- Extracted the main direction: Reconcile-OPSD / Fork-Preserving Judgment-Delta Self-Distillation.
- Confirmed the old `/data03/liang/mjy/safe_opd` directory already exists and should not be overwritten.
- Confirmed the `mjy` conda environment exists and can see 4 H100 PCIe GPUs.
- Confirmed several usable local models under `/data/LLM`.

## Current Blockers

- No GitHub remote URL has been configured yet.
- No DeepSeek-R1-Distill-Qwen model was found under `/data/LLM`.
- `mjy` currently lacks `bitsandbytes`, `deepspeed`, and `flash-attn`; this matters for QLoRA, multi-GPU training, and high-throughput long-context training.
- All 4 H100 GPUs had active processes during the initial survey, so no training should start without a fresh GPU check.

## Next Actions

- Ask ChatGPT Pro to investigate novelty/collision risks using the prepared context packet.
- Decide the first implementation target: data schema + action-mode labels, or baseline eval harness.
- Choose first smoke model: `Qwen2.5-7B-Instruct`, `Qwen3-8B`, or `YuFeng-XGuard-Reason-8B`.
- If DeepSeek-R1-Distill-Qwen is required, ask the user to download the 14B and/or 32B version.
- Before high-VRAM runs, decide whether to install `bitsandbytes`, `deepspeed`, and `flash-attn` into `mjy`.

