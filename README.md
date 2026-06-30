# Reconcile-OPSD

This repository is the working space for an OPD safety research project.

Working thesis:

> Distill safety-relevant judgment improvements into reasoning models under conflicting or ambiguous scenarios, while preserving exploration, backtracking, uncertainty expression, and useful reasoning forks.

The project should not be framed as "safe OPD". The intended direction is:

- reconciliation ability rather than refusal-only safety;
- judgment-delta self-distillation rather than full CoT imitation;
- fork-preserving adaptive OPD rather than uniform reverse-KL pressure;
- action-mode distillation rather than copying teacher reasoning text.

## Roles

- Codex: engineering execution, remote setup, experiments, logs, Git hygiene.
- ChatGPT Pro: research planning, literature triage, contribution analysis, experimental critique.
- Git: shared factual state for progress, accepted decisions, plans, and experiment evidence.

## Remote

- Host: `10.26.128.46`
- Project root: `/data03/liang/mjy/reconcile_opsd`
- Conda environment: `mjy`
- Model root: `/data/LLM` -> `/data01/LLM`
- Existing related but separate old project: `/data03/liang/mjy/safe_opd`

Credentials are documented in the local private file `.secrets/PROJECT_CREDENTIALS.md`, which is intentionally not tracked by Git.

