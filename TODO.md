# TODO

## Immediate

- Treat the current action-mode/REASON QLoRA runs as frozen negative-result baselines.
- Review the constrained scoring report and error table for clean/ambiguous/taxonomy-problem cases.
- Use the error table to mark clean/ambiguous/taxonomy-problem examples.
- Decide first-stage method name: `Reconcile-OPSD`, `Judgment-Delta Self-OPD`, or `Fork-Preserving Safety Distillation`.
- Keep R1/DeepSeek-R1-Distill out of first-stage experiments.
- Implement pairwise v0.1 plan from `docs/pairwise_v0_1_plan.md`.
- Move `continue_reasoning` out of final `primary_action` and into `fork_state` / `needs_more_reasoning`.
- Add `scope_contract` and wrong-scope direction fields.
- Regenerate pairwise v0.1 train/dev data and re-score Qwen3-8B 4-bit base.
- Add `reports/pairwise_v0_1_data_audit.*` for clean/ambiguous/taxonomy-problem pair review.
- Extend pairwise eval with hard-axis/source-level/fork-preservation/scope-contract metrics.
- Redesign `continue_reasoning` as a prefix-level fork-state target, not a final response action.

## Engineering

- Add experiment config templates.
- Add a helper that exports `CUDA_HOME=/usr/local/cuda-12.2` for deepspeed/flash-attn runs.
- Add a pairwise QLoRA trainer after v0.1 fork/scope scoring is in place.
- Persist `preflight_gpu.json`, `train_losses.jsonl`, and `metrics.json` for pairwise training runs.
- Add response-level generation/eval for `final_response`, eval-only for now.
- Add a classification-style or pairwise judgment-delta target option.
- Extend GPU/run helpers to write structured experiment preflight snapshots into each output directory.

## Research

- Literature scan: OPCD, OPSD, OPD for safety, safety reasoning, deliberative alignment, over-refusal, process supervision, CoT monitorability.
- Define fork/backtracking/uncertainty metrics.
- Define action-mode taxonomy.
- Design ablations.
