# TODO

## Immediate

- Ask ChatGPT Pro for a novelty/collision scan using `PRO_CONTEXT_PACKET.md`.
- Decide first-stage method name: `Reconcile-OPSD`, `Judgment-Delta Self-OPD`, or `Fork-Preserving Safety Distillation`.
- Define seed ReconcileBench schema and 20-50 examples.
- Decide first smoke model, with `Qwen3-8B` as the current default thinking-capable candidate.
- Run generation/template smoke checks before using any model in training or evaluation.
- Keep R1/DeepSeek-R1-Distill out of first-stage experiments.
- Expand the seed dataset from 12 examples toward at least 50 examples.
- Convert Qwen3-8B baseline failures into training/eval categories.

## Engineering

- Add a dataset schema validator.
- Add a small baseline evaluation harness.
- Add GPU logging utilities.
- Add model metadata and chat-template inspection utilities.
- Add a dry-run training script that loads a small model and one synthetic batch.
- Add experiment config templates.
- Add a helper that exports `CUDA_HOME=/usr/local/cuda-12.2` for deepspeed/flash-attn runs.
- Add a training data builder for action-mode labels and judgment-delta fields.

## Research

- Literature scan: OPCD, OPSD, OPD for safety, safety reasoning, deliberative alignment, over-refusal, process supervision, CoT monitorability.
- Define fork/backtracking/uncertainty metrics.
- Define action-mode taxonomy.
- Design ablations.
