# TODO

## Immediate

- Ask ChatGPT Pro for a novelty/collision scan using `PRO_CONTEXT_PACKET.md`.
- Decide first-stage method name: `Reconcile-OPSD`, `Judgment-Delta Self-OPD`, or `Fork-Preserving Safety Distillation`.
- Define a real train/dev split and expand ReconcileBench from 12 seed examples toward 50 examples.
- Keep R1/DeepSeek-R1-Distill out of first-stage experiments.
- Convert Qwen3-8B baseline failures into training/eval categories.
- Run the next Qwen3-8B QLoRA experiment only after the expanded dataset and dev split exist.

## Engineering

- Add GPU logging utilities.
- Add experiment config templates.
- Add a helper that exports `CUDA_HOME=/usr/local/cuda-12.2` for deepspeed/flash-attn runs.
- Add a training data builder for action-mode labels and judgment-delta fields.
- Add dataset split/export utilities once the seed set is expanded.
- Add a dataset taxonomy audit/report script for action-mode, scenario type, and risk-category balance.

## Research

- Literature scan: OPCD, OPSD, OPD for safety, safety reasoning, deliberative alignment, over-refusal, process supervision, CoT monitorability.
- Define fork/backtracking/uncertainty metrics.
- Define action-mode taxonomy.
- Design ablations.
