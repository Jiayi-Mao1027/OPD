# Project Status

Last updated: 2026-07-01 04:35 +08:00

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
- Reviewed the latest pairwise result with Pro and a method subagent.
- Added `docs/pairwise_v0_1_plan.md` to pin the next-stage decision: repair fork-state/scope-contract targets and eval before structured pairwise QLoRA.
- Added v0.1 enrichment, pairwise builder, data audit, and hard-axis pairwise eval support.
- Generated ReconcileBench v0.1 data and pairwise v0.1 data: `76` train pairs and `28` dev pairs, both audit-clean.
- Ran Qwen3-8B 4-bit base scoring on pairwise v0.1 dev: winner accuracy `0.7500` (`21/28`), missing `0`, parse failures `0`, average winner margin `1.8103`, peak allocated CUDA memory about `7217 MB`.
- v0.1 hard-axis result: fork-state remains `0/3`; scope-contract is `11/13 = 0.8462`.
- User clarified the training policy: do not use QLoRA or full-parameter fine-tuning; use rank-128 LoRA and control memory with batch size / gradient accumulation.
- Added `scripts/train_pairwise_lora.py` with default rank-128 non-quantized LoRA plus `--batch-size` and `--gradient-accumulation-steps`.
- Ran Qwen3-8B full/BF16 pairwise v0.1 control scoring: winner accuracy `0.7857`, fork-state `1/3`, scope-contract `11/13`, peak allocated CUDA memory about `15954 MB`.
- Ran rank-128 LoRA pairwise smoke tests on v0.1: structured target improves fork-state to `2/3` but drops overall winner accuracy to `0.6429`; winner-only target collapses toward `B` and drops to `0.3929`.
- Added position-balanced pairwise train/dev data and rank-128 non-QLoRA LoRA runs with compact structured targets.
- Current position-balanced compact LoRA status: mixed diagnostic under `score-mode=winner_only`; original dev improves to `23/28` with fork-state `2/3`, but position-balanced dev swap consistency remains below gate (`18/28` for `lr1e-5`, `19/28` for `lr3e-6_len1024`) and scope/refusal regressions remain.
- Added `score-mode=compact_structured_judgment` as a label-conditioned target-alignment diagnostic. It gives `28/28` original dev and `56/56` position-balanced dev for both rank-128 adapters, but this confirms compact target learning only and is not a standalone safety metric.
- Added parent-level swap diagnostics to pairwise evaluation reports.
- Added greedy compact-target generation parsing and evaluation.
- Ran Qwen3-8B compact generation checks for full BF16 base and the two rank-128 LoRA compact adapters on both original dev and position-balanced dev.
- Generation result: full BF16 base remains stronger than both adapters. On position-balanced dev, base gets `43/56 = 0.7679` winner accuracy and `19/28 = 0.6786` swap consistency; `r128_lr1e5` gets `39/56 = 0.6964` and `15/28 = 0.5357`; `r128_lr3e6_len1024` gets `42/56 = 0.7500` and `18/28 = 0.6429`.
- Compact generation confirms the earlier 100% compactscore result was optimistic/label-conditioned: all generation runs have `0.0000` full compact-target match.
- Documented this negative calibration result in `reports/pairwise_v0_1_compact_generation_summary.md`.
- Added `scripts/analyze_compact_generation_mismatches.py` and compact mismatch analysis support.
- Generated `reports/pairwise_v0_1_compact_generation_mismatch_analysis.md/json` and `reports/pairwise_v0_1_compact_generation_mismatch_samples.csv`.
- Mismatch finding: `full target match = 0.0000` is too strict as a standalone behavioral metric. Base and `r128_lr3e6_len1024` mostly emit only `WINNER` plus a schema-confused `DELTA_TAG`; `r128_lr1e5` emits nearly all fields but confuses `HARD_AXIS`, `DELTA_TAG`, and `SCOPE_ERROR_DIRECTION`.
- Added `--prompt-style ontology` for compact generation. It lists exact labels without changing the shared compact target or training target.
- Ran eval-only ontology-prompt compact generation for full BF16 base and both rank-128 compact adapters on original and position-balanced dev.
- Ontology prompt result: it removes schema-level confusion and gives `r128_lr1e5` a small strict full-target match (`0.1071` original, `0.0893` posbalanced), but it sharply worsens winner selection and side balance. On position-balanced dev, full base drops from `43/56 = 0.7679` to `34/56 = 0.6071`; `r128_lr1e5` drops from `39/56 = 0.6964` to `36/56 = 0.6429`; `r128_lr3e6_len1024` drops from `42/56 = 0.7500` to `35/56 = 0.6250`.
- Documented the ontology prompt result in `reports/pairwise_v0_1_compact_ontology_generation_summary.md`.

## Current Blockers

- No DeepSeek-R1-Distill-Qwen model was found under `/data/LLM`.
- All 4 H100 GPUs had active processes during the initial survey, so no training should start without a fresh GPU check.
- Some local model names are ambiguous; every chosen model still needs a generation smoke test before training/evaluation.
- R1/DeepSeek-R1-Distill experiments are deferred for now.
- First-stage experiments should use 8B or smaller models where possible.
- Deepspeed/flash-attn workflows must set `CUDA_HOME=/usr/local/cuda-12.2`.
- First-stage Qwen3-8B scripts use `attn_implementation=eager` and do not require `flash-attn`.
- The earlier QLoRA result is only a frozen training/eval plumbing smoke; it does not improve quality on the seed set and is not the current training path.
- ReconcileBench v0 is synthetic/seed-quality data for method iteration, not a publishable benchmark yet.
- The current v0 QLoRA run is a negative result: lower dev accuracy and repetitive reason generation.
- Normalized reasons fix the repetition issue but still do not produce a positive dev signal.
- The next contribution signal must come from structured judgment/audit or pairwise ranking, not from continuing the same SFT target.
- The current one-shot compact target is overloaded: explicit label ontology improves some metadata-field formatting but harms winner selection, so continuing the same compact target with more steps is not justified before redesign.

## Next Actions

- Treat position-balanced compact rank-128 LoRA as a negative generation result for now. The earlier winner-only/compactscore/ontology results were useful diagnostics, and they show the one-shot compact field target needs decomposition before more training steps.
- Ask Pro to review the compact generation, mismatch, and ontology-prompt result once browser access is stable.
- Next validation should be a reduced generation target (`WINNER` plus one observable rationale tag), a constrained multi-field scorer, a newly held-out fork/scope pairwise set, or human/external audit of assistant-facing responses.
- Use parent-level swap diagnostics to focus on `scope_contract/wrong_scope/unsafe_specificity` failures before adding more training steps.
- Prefer `Qwen3-8B` for the first thinking-model path; keep Qwen2.5 Instruct as a non-thinking baseline.
