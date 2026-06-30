# Project Status

Last updated: 2026-07-01 00:39 +08:00

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
- Added a minimal QLoRA training smoke for Qwen3-8B action-mode labels.
- Ran the QLoRA smoke on 4 seed examples for 2 steps: loss `5.6548 -> 3.3280`, peak allocated CUDA memory about `9355 MB`, adapter saved under ignored `outputs/train_smoke/qwen3_8b_action_lora_steps2/adapter`.
- Added adapter-aware prediction support to `scripts/generate_action_mode_predictions.py`.
- Evaluated the 2-step QLoRA smoke adapter against a 4-bit base control with the same train prompt: both got `0.1667` action-mode accuracy on the 12 seed examples.
- Added `docs/action_mode_label_guide.md` to pin down the seven current action-mode labels and common boundary cases.
- Added dataset audit/split tooling.
- Expanded ReconcileBench to `data/reconcilebench_v0.jsonl`: 52 examples, all seven action modes covered, no duplicate ids.
- Created a fixed split under `data/splits/`: 38 train examples and 14 dev examples, with exactly two dev examples per action mode.
- Extended the QLoRA trainer to optionally run dev generation/evaluation after training.
- Ran Qwen3-8B v0 20-step QLoRA: train loss dropped `5.9287 -> 1.7881`, but dev action-mode accuracy fell from the 4-bit base control `0.4286` to adapter `0.3571`.
- Added `--target-style normalized_reason` to reduce noisy `judgment_delta` targets.
- Ran Qwen3-8B v0 20-step QLoRA with normalized reasons: dev action-mode accuracy recovered to `0.4286`, matching but not beating the 4-bit base control; repeated reason generation mostly disappeared.
- Added GPU status/selection utilities and tests.
- Added a standard Qwen3-8B v0 QLoRA run wrapper that checks tests, selects a low-conflict GPU, exports CUDA env, and writes metrics.
- Added reference experiment configs for the current judgment-delta and normalized-reason v0 runs.
- Collected two ChatGPT Pro reviews of the v0 negative result and compared them in `PRO_COMPARISON_2026-06-30.md`.
- Decided to freeze the current action-mode/REASON SFT line and move next to constrained scoring, audit reports, and pairwise judgment-delta data.
- Added optional schema fields for decision axes: `primary_action`, `acceptable_actions`, `risk_type`, `can_answer`, `missing_critical_info`, `allowed_scope`, `needs_clarification`, `needs_uncertainty_expression`, `context_conflict`, and `needs_more_reasoning`.
- Added structured action-mode metrics and reporting support for per-mode F1, allowed-set accuracy, top-2 allowed accuracy, gold margin, entropy, confusion matrices, and hard-boundary confusions.
- Added constrained action-mode logprob scoring via `scripts/score_action_modes.py`.
- Ran constrained scoring on the v0 dev split for the Qwen3-8B 4-bit base control and normalized-reason adapter.
- Generated `reports/reconcile_v0_eval_base_vs_qlora.md`, `reports/reconcile_v0_error_table.csv`, and terminal-only variants.
- Constrained scoring result: both runs remain `0.4286` all-mode accuracy; normalized adapter improves macro-F1 `0.2880 -> 0.3293` and top-2 allowed accuracy `0.5714 -> 0.7143`.
- Added pairwise judgment-delta data builder and tests.
- Generated pairwise v0 data: `76` train pairs from `38` source examples and `28` dev pairs from `14` source examples, with no forbidden source-id or prompt-hash overlap.
- Added pairwise winner-scoring and evaluation tooling with unit tests.
- Ran Qwen3-8B 4-bit base pairwise scoring on the v0 dev pairs: winner accuracy `0.6786` (`19/28`) with about `7217 MB` peak allocated CUDA memory.
- Generated `reports/pairwise_v0_dev_base_eval.md`, `reports/pairwise_v0_dev_base_eval.json`, and `reports/pairwise_v0_dev_base_errors.csv`.
- Pairwise weak spots are concentrated in `continue_reasoning` / `lost_fork_state` (`0/4`) and `partial_allowed` / `wrong_scope` (`1/4`).

## Current Blockers

- No DeepSeek-R1-Distill-Qwen model was found under `/data/LLM`.
- All 4 H100 GPUs had active processes during the initial survey, so no training should start without a fresh GPU check.
- Some local model names are ambiguous; every chosen model still needs a generation smoke test before training/evaluation.
- R1/DeepSeek-R1-Distill experiments are deferred for now.
- First-stage experiments should use 8B or smaller models where possible.
- Deepspeed/flash-attn workflows must set `CUDA_HOME=/usr/local/cuda-12.2`.
- First-stage Qwen3-8B scripts use `attn_implementation=eager` and do not require `flash-attn`.
- The current QLoRA result is only a training/eval plumbing smoke; it does not improve quality on the seed set.
- ReconcileBench v0 is synthetic/seed-quality data for method iteration, not a publishable benchmark yet.
- The current v0 QLoRA run is a negative result: lower dev accuracy and repetitive reason generation.
- Normalized reasons fix the repetition issue but still do not produce a positive dev signal.
- The next contribution signal must come from structured judgment/audit or pairwise ranking, not from continuing the same SFT target.

## Next Actions

- Audit the pairwise v0 data and base errors for template/taxonomy quality before training.
- Ask Pro/subagents to review whether the next step should be pairwise QLoRA, fork-state retargeting, or data revision.
- Split `continue_reasoning` out of root terminal action-mode evaluation and into a prefix-level fork-state target.
- Prefer `Qwen3-8B` for the first thinking-model path; keep Qwen2.5 Instruct as a non-thinking baseline.
