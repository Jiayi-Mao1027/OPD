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
- Use the new `compact_winner_obs_tag` target before trying any more rationale-label training. It emits `WINNER` plus an observable `OBS_TAG` derived from winner action mode, with `preserve_fork_state` for fork-state/lost-fork records.
- Run eval-only `compact_winner_obs_tag` generation for full BF16 base and the existing rank-128 winner-delta adapter on original and position-balanced dev before launching another LoRA run.
- Consider a batch-size 3 rank-128 LoRA probe only if a fresh GPU check shows enough free memory; batch size 2 reached about `35.8GB` process peak and around `67GB` total observed GPU1 usage, below the preferred `70GB+` target.
- Build a newly held-out fork/scope pairwise set or run human/external audit of assistant-facing responses.
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
