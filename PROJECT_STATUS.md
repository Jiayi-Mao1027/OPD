# Project Status

Last updated: 2026-07-01 13:17 +08:00

## Current Objective

Freeze the current negative proxy-training lines and move to a candidate-local reconciliation scorer that is validated by position-invariant pairwise gates and assistant-facing response-selection audits.

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
- Tried to hand off the updated compact-generation packet to the open ChatGPT Pro conversation, but Chrome tab claiming timed out twice, including one 5-minute attempt. The Pro review packet remains ready in `PRO_REVIEW_PACKET_2026-07-01.md`.
- Added the reduced pairwise compact target `compact_winner_delta_tag`, which trains/generates only `WINNER` and `DELTA_TAG` while keeping the full compact target as the default diagnostic path.
- Updated `scripts/train_pairwise_lora.py` and `scripts/generate_pairwise_compact_judgments.py` to support `--target-style compact_winner_delta_tag`.
- Verified local tests after the reduced-target implementation: `55 passed`.
- Ran `compact_winner_delta_tag` rank-128 LoRA on Qwen3-8B with no QLoRA/no full fine-tuning: batch size `2`, grad accumulation `8`, 24 steps, lr `3e-6`, max length `1024`. Loss dropped `4.3336 -> 0.7752`; peak allocated training memory was `35752.42 MB`.
- Added direct-script `src` path fallbacks to pairwise scoring/eval CLIs after the remote resume job exposed a missing `PYTHONPATH` failure.
- Ran winner-only scoring and reduced generation for the batch-2 winner-delta adapter against full BF16 base on original and position-balanced dev.
- Winner-only result: original dev ties full base at `22/28 = 0.7857`; position-balanced dev gets `43/56 = 0.7679`, with better A/B balance (`27/29`) and slightly better swap consistency (`19/28 = 0.6786`) than full base (`18/28`), but still fails the `0.70` swap gate.
- Reduced generation result: adapter beats reduced-prompt full base on winner accuracy (`23/28` vs `22/28` original; `45/56` vs `41/56` position-balanced), improves fork on position-balanced dev to `5/6`, and has better side balance (`31/25`). It still fails swap consistency by one parent pair (`19/28 = 0.6786`) and has `0` exact `DELTA_TAG` matches.
- Documented this in `reports/pairwise_v0_1_winner_delta_summary.md` plus the winner-only, generation, and mismatch reports.
- Added and ran a separate constrained `DELTA_TAG` scorer conditioned on the gold winner. It also failed to recover the current discrete tag labels: full base `6/28` original and `11/56` position-balanced; rank-128 winner-delta adapter `6/28` original and `10/56` position-balanced.
- Added `compact_winner_obs_tag`, a reduced generation/training target with only `WINNER` and `OBS_TAG`.
- `OBS_TAG` is deterministically derived from the winner card's visible action mode, with `preserve_fork_state` overriding ordinary actions for fork-state/lost-fork cases.
- Local and remote verification after the new target implementation: `python -m pytest -q` -> `60 passed`.
- Ran eval-only `compact_winner_obs_tag` generation for full BF16 Qwen3-8B and the existing rank-128 winner-delta adapter.
- Observable-tag generation result: the existing adapter beats full base on original dev (`23/28` vs `22/28`) and position-balanced dev (`44/56` vs `42/56`), improves fork-state on position-balanced dev (`5/6` vs `4/6`), and passes the current position-bias gate with swap consistency `20/28 = 0.7143`.
- Documented this in `reports/pairwise_v0_1_obs_tag_generation_summary.md` and the original/position-balanced obs-tag generation reports.
- Ran a `compact_winner_obs_tag` rank-128 LoRA training probe. Batch size `3` OOMed under shared GPU load; batch size `2`, gradient accumulation `8`, max length `1024`, 24 steps, lr `3e-6` completed without QLoRA or full-parameter fine-tuning.
- Completed obs-tag LoRA training loss `6.4620 -> 0.7934`, process peak allocated CUDA memory `35413.57 MB`, and observed GPU1 total memory up to `78328 MB`.
- Added a fresh Chinese fork/scope heldout diagnostic set: 16 source examples, 48 pairwise records, and 96 position-balanced records.
- Fixed `src/reconcile_opsd/pairwise_data.py::render_card` so newly generated pairwise inputs keep decision-card fields on separate lines; added a regression test.
- Rebuilt the fresh heldout pairwise files after the render fix. Existing train/dev pairwise JSONL files were not regenerated, so historical training/eval remains tied to the old rendering.
- Heldout audit is clean: position-balanced heldout has `96/96` clean records and no forbidden source-id or prompt-hash overlap against existing v0.1 train/dev.
- Ran full BF16 base, existing rank-128 winner-delta adapter, and new rank-128 obs-tag adapter on fresh heldout under `compact_winner_obs_tag` generation.
- Fresh position-balanced heldout result: fullbase `61/96 = 0.6354`, existing adapter `68/96 = 0.7083`, new obs-tag adapter `68/96 = 0.7083`. Both adapters improve over base but fail the swap gate at `32/48 = 0.6667`.
- Documented the training, dev eval, heldout eval, render caveat, and next recommendation in `reports/pairwise_v0_1_obs_tag_adapter_and_heldout_summary.md`.
- Added reusable parent-level swap-failure analysis via `scripts/analyze_pairwise_swap_failures.py`.
- Generated `reports/pairwise_v0_1_heldout_fork_scope_swap_failure_analysis.md/json/csv`. Fullbase has `21/48` inconsistent parents, all locked to A; both adapters reduce this to `16/48`, fix 12 fullbase failures, add 7 new failures, and leave 7 persistent failures across all runs.
- Added response-level assistant generation and heuristic audit tooling via `scripts/generate_response_level_outputs.py` and `scripts/audit_response_level_outputs.py`.
- Ran the first assistant-facing heldout smoke on the 16 fresh fork/scope prompts for full BF16 Qwen3-8B, the existing rank-128 winner-delta adapter, and the new rank-128 obs-tag adapter.
- Response-level heldout result is mixed/negative: fullbase has the best heuristic overall pass (`6/16`) and lowest manual-review rate (`10/16`), while the obs-tag adapter gets `5/16` overall pass and the winner-delta adapter gets `3/16`.
- Documented this in `reports/response_level_v0_1_heldout_fork_scope_audit.md/json/csv` and added the result to `reports/pairwise_v0_1_obs_tag_adapter_and_heldout_summary.md`.
- Added `--prompt-style direct|boundary_plan` for response-level generation, strict post-think / `FINAL_RESPONSE` extraction in the audit, and regression tests for reference isolation and parse failures.
- Ran the eval-only boundary-plan bridge at `max_new_tokens=1024` for fullbase and both rank-128 adapters. All runs had closed thinking; all boundary-plan rows had parseable `FINAL_RESPONSE`.
- Boundary-plan bridge result is negative: fullbase direct `5/16` vs boundary `1/16`; winner-delta direct `3/16` vs boundary `2/16`; obs-tag direct `4/16` vs boundary `1/16`.
- Documented this in `reports/response_level_v0_1_boundary_bridge_summary.md` and `reports/response_level_v0_1_heldout_fork_scope_boundary_bridge_1024_audit.md/json/csv`.
- Added and ran response-level rank-128 final-response LoRA SFT on the 38-example v0.1 train split.
- Response-level SFT is negative: with thinking, fullbase direct1024 gets `5/16` overall while response-SFT gets `4/16`; without thinking, fullbase gets `7/16` while response-SFT gets `5/16`.
- Documented this in `reports/response_level_v0_1_response_sft_summary.md` and the direct1024 response-SFT audit reports.
- Sent the latest compact, heldout, response-level SFT, and boundary-bridge results to ChatGPT Pro from the main Codex controller.
- Pro advice treated the current evidence as diagnostic rather than method-success evidence. The strongest recommended next path is a candidate-local constrained scorer that predicts `ACCEPTABLE` and one observable `ERROR_TAG`, then induces pairwise winners by independently scoring both candidates.

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
- ChatGPT Pro browser handoff is temporarily blocked by Chrome tab-claim timeouts, not by missing project context.
- `compact_winner_delta_tag` gives a real preliminary winner-generation signal, but it is not a passed method result because position-balanced swap consistency is still below gate and `DELTA_TAG` exact accuracy is `0`.
- The current discrete `DELTA_TAG` ontology is not learned even under constrained scoring, so additional training on the same tag labels is unlikely to be useful before relabeling/redesign.
- Historical train/dev pairwise JSONL files still contain the earlier `render_card` field-concatenation formatting. Newly generated heldout files are fixed, but do not retroactively claim historical training used fixed rendering.
- The fresh heldout set is a small Chinese fork/scope diagnostic set, not a full benchmark. It does not cover `ask_clarification`, `direct_answer`, or `refuse` as source action modes.
- The new obs-tag adapter improves `OBS_TAG` exact matching (`38/96` vs `20/96` for the existing adapter on position-balanced heldout), but it does not improve primary winner/swap metrics over the existing winner-delta adapter.
- Both rank-128 adapters beat fullbase on fresh heldout winner accuracy, but both fail the current position-balanced swap gate (`32/48 = 0.6667`, below `0.70`).
- The first response-level audit does not show transfer from pairwise winner signal to better assistant-facing responses. Treat it as heuristic triage, not a final safety judge, but do not continue the same target as a positive result.
- A simple boundary-plan prompt bridge also does not transfer the pairwise signal. The strict 1024-token audit shows boundary planning worsens final-answer behavior under the current heuristic metric.
- Response-level final-response SFT on the current 38 examples is also negative and should not be continued by simply adding more steps.
- Current evidence does not support a claim that Reconcile-OPSD improves assistant-facing safety behavior. It supports a diagnostic failure-map claim and a candidate-local scorer hypothesis.
- Pro warned that novelty is not defensible as generic "OPD for safety", "self-OPD for safety", or "reasoning safety beyond refusal"; those collide with prior OPSD/OPCD/OPSA, deliberative safety reasoning, RATIONAL-style context-aware safety reasoning, pairwise preference learning, and judge position-bias work.

## Next Actions

- Treat position-balanced compact rank-128 LoRA, boundary-plan prompting, and response-level final-response SFT as frozen negative diagnostics.
- Build v0.2 candidate-local data from current pairwise examples: score each candidate independently with `ACCEPTABLE: yes/no` and `ERROR_TAG: none | fork_state | scope_contract | wrong_scope | unsafe_specificity | over_refusal | missing_clarification`.
- Evaluate fullbase and prompted-base candidate-local scoring before training. If prompted base solves the task, the benchmark is too easy.
- If the baseline is not solved, train one rank-128 non-QLoRA candidate-local constrained scorer with short context and no final-response SFT.
- Induce pairwise winners from independent candidate scores, then require fresh winner accuracy around `>= 0.75`, swap consistency `>= 0.75` preferably `>= 0.80`, small position gap, and no material scope/refusal regression before calling it a method signal.
- After a scorer passes pairwise gates, test assistant-facing transfer by generating multiple fullbase candidate responses, scoring/selecting with the candidate-local scorer, and auditing selected responses against greedy fullbase.
- Do not claim the new obs-tag adapter as a passed method result. Treat it as support-label learning plus a fresh-heldout winner signal that still needs position-invariance repair.
- Inspect the seven persistent heldout swap failures and seven adapter-new failures, especially `scope_contract/wrong_scope`, `unsafe_specificity`, and fork-preservation cases.
- Use the response-level audit to choose failure cases for human/external-judge review before more training on generator targets.
- Do not claim the pairwise adapters improve final assistant behavior yet. Fullbase is ahead on the current 16-case heuristic response-level audit.
- Do not continue prompt-bridge experiments, compact multi-field generation, pairwise WINNER generation, or 38-example final-response SFT as the main path.
- Use parent-level swap diagnostics to focus on `scope_contract/wrong_scope/unsafe_specificity` failures before adding more training steps.
- Prefer `Qwen3-8B` for the first thinking-model path; keep Qwen2.5 Instruct as a non-thinking baseline.
