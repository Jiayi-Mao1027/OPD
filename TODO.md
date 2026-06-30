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
- Ask Pro to review the compact generation mismatch, ontology-prompt result, and reduced-target next step once browser access is stable. The Chrome handoff packet is already prepared, but claiming the ChatGPT tab timed out on 2026-07-01.
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
- Add response-level assistant generation/eval or human/external audit before more training on the same target.
- Use parent-level swap diagnostics to focus on `scope_contract/wrong_scope/unsafe_specificity` failures before adding more training steps.
- Redesign `continue_reasoning` as a prefix-level fork-state target, not a final response action.

## Engineering

- Add experiment config templates.
- Add a helper that exports `CUDA_HOME=/usr/local/cuda-12.2` for deepspeed/flash-attn runs.
- Keep `scripts/train_pairwise_lora.py` as the pairwise trainer; default rank-128 LoRA, no quantization.
- Keep `scripts/generate_pairwise_compact_judgments.py` as the generation-side check for compact target claims.
- Keep `scripts/analyze_compact_generation_mismatches.py` as the raw-generation mismatch report for compact target claims.
- Use `--target-style compact_winner_obs_tag` for the next pairwise LoRA/generation ablation; `compact_winner_delta_tag` is retained only as a logged negative/reduced-label diagnostic, and full compact remains available as `compact_structured_judgment` for diagnostics.
- Keep `--prompt-style ontology` eval-only; do not make it the default compact generation prompt.
- Persist `preflight_gpu.json`, `train_losses.jsonl`, and `metrics.json` for pairwise training runs.
- Add response-level generation/eval for `final_response`, eval-only for now.
- Add a classification-style or pairwise judgment-delta target option.
- Extend GPU/run helpers to write structured experiment preflight snapshots into each output directory.

## Research

- Literature scan: OPCD, OPSD, OPD for safety, safety reasoning, deliberative alignment, over-refusal, process supervision, CoT monitorability.
- Define fork/backtracking/uncertainty metrics.
- Define action-mode taxonomy.
- Design ablations.
