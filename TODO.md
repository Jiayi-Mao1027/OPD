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
- Run the implemented reduced target `compact_winner_delta_tag` (`WINNER` plus observable `DELTA_TAG`) before adding more steps to the old one-shot compact target.
- If reduced generation still improves only formatting, move `DELTA_TAG` to a separate constrained scorer instead of expanding the target again.
- Build a newly held-out fork/scope pairwise set or run human/external audit of assistant-facing responses.
- Use parent-level swap diagnostics to focus on `scope_contract/wrong_scope/unsafe_specificity` failures before adding more training steps.
- Redesign `continue_reasoning` as a prefix-level fork-state target, not a final response action.

## Engineering

- Add experiment config templates.
- Add a helper that exports `CUDA_HOME=/usr/local/cuda-12.2` for deepspeed/flash-attn runs.
- Keep `scripts/train_pairwise_lora.py` as the pairwise trainer; default rank-128 LoRA, no quantization.
- Keep `scripts/generate_pairwise_compact_judgments.py` as the generation-side check for compact target claims.
- Keep `scripts/analyze_compact_generation_mismatches.py` as the raw-generation mismatch report for compact target claims.
- Use `--target-style compact_winner_delta_tag` for the next pairwise LoRA/generation ablation; full compact remains available as `compact_structured_judgment` for diagnostics.
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
