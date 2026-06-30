# TODO

## Immediate

- Ask ChatGPT Pro for a novelty/collision scan using `PRO_CONTEXT_PACKET.md`.
- Decide first-stage method name: `Reconcile-OPSD`, `Judgment-Delta Self-OPD`, or `Fork-Preserving Safety Distillation`.
- Define seed ReconcileBench schema and 20-50 examples.
- Decide first smoke model, with `Qwen3-8B` as the current default thinking-capable candidate.
- Decide whether to install missing training dependencies in `mjy`.
- Run generation/template smoke checks before using any model in training or evaluation.

## Engineering

- Add a dataset schema validator.
- Add a small baseline evaluation harness.
- Add GPU logging utilities.
- Add model metadata and chat-template inspection utilities.
- Add a dry-run training script that loads a small model and one synthetic batch.
- Add experiment config templates.

## Research

- Literature scan: OPCD, OPSD, OPD for safety, safety reasoning, deliberative alignment, over-refusal, process supervision, CoT monitorability.
- Define fork/backtracking/uncertainty metrics.
- Define action-mode taxonomy.
- Design ablations.
