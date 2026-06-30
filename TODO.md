# TODO

## Immediate

- Ask ChatGPT Pro for a novelty/collision scan using `PRO_CONTEXT_PACKET.md`.
- Ask ChatGPT Pro to review the v0 QLoRA negative result and recommend the next ablation.
- Decide first-stage method name: `Reconcile-OPSD`, `Judgment-Delta Self-OPD`, or `Fork-Preserving Safety Distillation`.
- Keep R1/DeepSeek-R1-Distill out of first-stage experiments.
- Convert Qwen3-8B baseline failures into training/eval categories.
- Add response-level evaluation beyond explicit `ACTION_MODE` labels.
- Redesign `ask_clarification` and `continue_reasoning` targets; they remain weak after normalized-reason training.

## Engineering

- Add GPU logging utilities.
- Add experiment config templates.
- Add a helper that exports `CUDA_HOME=/usr/local/cuda-12.2` for deepspeed/flash-attn runs.
- Add a training data builder for action-mode labels and judgment-delta fields.
- Add response-level generation/eval for `final_response`.
- Add a classification-style or pairwise judgment-delta target option.

## Research

- Literature scan: OPCD, OPSD, OPD for safety, safety reasoning, deliberative alignment, over-refusal, process supervision, CoT monitorability.
- Define fork/backtracking/uncertainty metrics.
- Define action-mode taxonomy.
- Design ablations.
