# TODO

## Immediate

- Treat the current action-mode/REASON QLoRA runs as frozen negative-result baselines.
- Review the constrained scoring report and error table for clean/ambiguous/taxonomy-problem cases.
- Use the error table to mark clean/ambiguous/taxonomy-problem examples.
- Decide first-stage method name: `Reconcile-OPSD`, `Judgment-Delta Self-OPD`, or `Fork-Preserving Safety Distillation`.
- Keep R1/DeepSeek-R1-Distill out of first-stage experiments.
- Review v0.1 base errors, especially the three fork-state failures.
- Keep all next training runs as rank-128 LoRA, not QLoRA and not full-parameter fine-tuning.
- Use `--batch-size` and `--gradient-accumulation-steps` to manage memory.
- Treat position-balanced compact rank-128 LoRA as a negative generation result until a stronger validation passes. Winner-only, compactscore, mismatch, and ontology-prompt diagnostics do not support the current one-shot compact target.
- ChatGPT Pro reviewed the compact, heldout, response-level SFT, and boundary-bridge results on 2026-07-01. Treat the advice as research guidance: the current evidence is diagnostic, not method success.
- Treat the completed `compact_winner_delta_tag` run as a preliminary winner-generation signal, not a passed method result: generation beats reduced-prompt base, but swap consistency is still `19/28` and `DELTA_TAG` exact accuracy is `0`.
- Stop training/scoring the current discrete `DELTA_TAG` labels as a positive target: constrained scoring also failed (`6/28` original, `10/56` adapter posbalanced).
- Treat the completed eval-only `compact_winner_obs_tag` result as the current best pairwise generation diagnostic: existing rank-128 winner-delta adapter gets `44/56` on position-balanced dev, swap `20/28 = 0.7143`, and passes the current position-bias gate.
- `compact_winner_obs_tag` rank-128 LoRA has been trained and checked on fresh heldout. Treat it as a mixed diagnostic, not a passed method result: it improves `OBS_TAG` exact matching, but does not beat the existing winner-delta adapter on primary winner/swap metrics.
- Fresh fork/scope heldout is built: 16 source examples, 48 pairwise records, 96 position-balanced records, audit clean, no source-id or prompt-hash overlap with v0.1 train/dev.
- Fresh position-balanced heldout result: fullbase `61/96`, existing winner-delta adapter `68/96`, new obs-tag adapter `68/96`; both adapters fail swap gate at `32/48 = 0.6667`.
- Do not claim `OBS_TAG` label learning as the contribution. Exact `OBS_TAG` improves to `38/96` on fresh position-balanced heldout, but the main gate remains winner accuracy, side balance, and parent-level swap consistency.
- Keep the render-format caveat visible: newly generated heldout pairwise files have fixed `render_card` newlines; historical train/dev pairwise files still use the earlier concatenated-field rendering.
- Parent-level heldout swap-failure analysis is now generated in `reports/pairwise_v0_1_heldout_fork_scope_swap_failure_analysis.md`.
- Inspect the seven persistent inconsistent parents and the seven adapter-new inconsistent parents before adding more training. The main remaining axes are `scope_contract` and `fork_state`; the adapter failures include more B-side locking than fullbase.
- Response-level assistant generation/eval is now implemented for the fresh fork/scope heldout set. Treat the first heuristic smoke as mixed/negative: fullbase overall pass `6/16`, new obs-tag adapter `5/16`, existing winner-delta adapter `3/16`.
- Boundary-plan prompt bridge has been tested as eval-only and is negative under strict post-think / `FINAL_RESPONSE` auditing: fullbase `5/16 -> 1/16`, winner-delta `3/16 -> 2/16`, obs-tag `4/16 -> 1/16`.
- Do not use the earlier 320-token boundary-plan smoke as evidence. It was confounded by truncated thinking and whole-generation fallback before strict final-answer parsing.
- Do not continue the same pairwise target as a positive assistant-behavior path until response-level failures are manually or externally judged.
- Response-level final-response SFT is also a negative diagnostic: on the 16-case fresh fork/scope heldout audit, fullbase beats response-SFT both with thinking (`5/16` vs `4/16`) and without thinking (`7/16` vs `5/16`).
- Freeze the current proxy-training branches as negative diagnostics: action-mode SFT, compact pairwise generation, boundary-plan bridge, and 38-example final-response SFT.
- Do not continue pairwise `WINNER` generation, compact multi-field generation, boundary-plan prompting, or final-response SFT as the main path.
- v0.2 candidate-local data and tooling are built. Current generated sets: train `152`, dev `56`, dev position-balanced `112`, fresh fork/scope heldout `96`, and fresh heldout position-balanced `192` candidate examples.
- Evaluate fullbase and prompted-base candidate-local scoring before any new training. Track acceptable macro-F1, error-tag macro-F1, induced pairwise winner accuracy, swap consistency, per-stratum recall, and gold-vs-confuser margin.
- Only if baseline scoring leaves room, train one rank-128 non-QLoRA candidate-local constrained scorer with short context and no final-response target.
- Gate any method claim on fresh induced pairwise winner accuracy around `>= 0.75`, swap consistency `>= 0.75` preferably `>= 0.80`, small position gap, fork/scope accuracy above fullbase, and no material scope/refusal regression.
- If candidate-local scoring passes pairwise gates, test assistant-facing transfer through response selection: generate multiple fullbase candidate responses, score/select with the candidate-local scorer, then audit selected responses against greedy fullbase.
- Use parent-level swap diagnostics to focus on `scope_contract/wrong_scope/unsafe_specificity` failures before adding more training steps.
- Redesign `continue_reasoning` as a prefix-level fork-state target, not a final response action.

## Engineering

- Add experiment config templates.
- Add a helper that exports `CUDA_HOME=/usr/local/cuda-12.2` for deepspeed/flash-attn runs.
- Keep `scripts/train_pairwise_lora.py` as the pairwise trainer; default rank-128 LoRA, no quantization.
- Keep `scripts/generate_pairwise_compact_judgments.py` as the generation-side check for compact target claims.
- Keep `scripts/analyze_compact_generation_mismatches.py` as the raw-generation mismatch report for compact target claims.
- Keep `compact_winner_obs_tag`, `compact_winner_delta_tag`, and full compact targets as logged diagnostics. Do not make them the next main training path without a new decision.
- Keep `--prompt-style ontology` eval-only; do not make it the default compact generation prompt.
- Persist `preflight_gpu.json`, `train_losses.jsonl`, and `metrics.json` for pairwise training runs.
- Keep `scripts/generate_response_level_outputs.py` and `scripts/audit_response_level_outputs.py` as eval-only assistant-facing smoke tooling. The current audit is heuristic triage, not a final safety judge.
- Keep strict response extraction: audit post-`</think>` visible text only, and for `boundary_plan` audit only `FINAL_RESPONSE`; parse failures should not fall back to scoring the plan.
- Keep `scripts/build_candidate_local_data.py`, `scripts/score_candidate_local.py`, and `scripts/evaluate_candidate_local_scores.py` as the v0.2 candidate-local scoring path.
- Extend GPU/run helpers to write structured experiment preflight snapshots into each output directory.

## Research

- Literature scan / framing guardrails: OPCD, OPSD, OPSA, RATIONAL-style context-aware safety reasoning, deliberative alignment, trace-level safety detection, pairwise preference learning, and LLM-as-judge position bias.
- Define fork/backtracking/uncertainty metrics.
- Define action-mode taxonomy.
- Design ablations.
