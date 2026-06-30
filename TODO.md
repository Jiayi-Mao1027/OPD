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
- Ask Pro to analyze why rank-128 structured LoRA improves fork-state but collapses overall/scope, and why winner-only collapses toward `B`.
- Add a balanced structured target or sampler that addresses A/B position bias and hard-axis weighting.
- Redesign `continue_reasoning` as a prefix-level fork-state target, not a final response action.

## Engineering

- Add experiment config templates.
- Add a helper that exports `CUDA_HOME=/usr/local/cuda-12.2` for deepspeed/flash-attn runs.
- Keep `scripts/train_pairwise_lora.py` as the pairwise trainer; default rank-128 LoRA, no quantization.
- Persist `preflight_gpu.json`, `train_losses.jsonl`, and `metrics.json` for pairwise training runs.
- Add response-level generation/eval for `final_response`, eval-only for now.
- Add a classification-style or pairwise judgment-delta target option.
- Extend GPU/run helpers to write structured experiment preflight snapshots into each output directory.

## Research

- Literature scan: OPCD, OPSD, OPD for safety, safety reasoning, deliberative alignment, over-refusal, process supervision, CoT monitorability.
- Define fork/backtracking/uncertainty metrics.
- Define action-mode taxonomy.
- Design ablations.
