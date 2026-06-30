# TODO

## Immediate

- Ask ChatGPT Pro for a novelty/collision scan using `PRO_CONTEXT_PACKET.md`.
- Decide first-stage method name: `Reconcile-OPSD`, `Judgment-Delta Self-OPD`, or `Fork-Preserving Safety Distillation`.
- Keep R1/DeepSeek-R1-Distill out of first-stage experiments.
- Convert Qwen3-8B baseline failures into training/eval categories.
- Run the next Qwen3-8B QLoRA experiment on `data/splits/reconcilebench_v0_train.jsonl` and evaluate on `data/splits/reconcilebench_v0_dev.jsonl`.
- Add response-level evaluation beyond explicit `ACTION_MODE` labels.

## Engineering

- Add GPU logging utilities.
- Add experiment config templates.
- Add a helper that exports `CUDA_HOME=/usr/local/cuda-12.2` for deepspeed/flash-attn runs.
- Add a training data builder for action-mode labels and judgment-delta fields.
- Extend training to consume the fixed v0 train/dev split and write eval summaries.

## Research

- Literature scan: OPCD, OPSD, OPD for safety, safety reasoning, deliberative alignment, over-refusal, process supervision, CoT monitorability.
- Define fork/backtracking/uncertainty metrics.
- Define action-mode taxonomy.
- Design ablations.
