# Decisions

## 2026-06-30 - Use a new project directory

Decision: create and use `/data03/liang/mjy/reconcile_opsd`.

Reason: `/data03/liang/mjy/safe_opd` already exists and appears to be a separate older SafeOPD project with code, checkpoints, logs, and its own `AGENTS.md`.

Impact: old SafeOPD can be used as reference material later, but this project must not overwrite it.

## 2026-06-30 - Frame the project around reconciliation, not safe OPD

Decision: frame the project as Reconcile-OPSD / Fork-Preserving Judgment-Delta Self-Distillation.

Reason: the web-chat research discussion and subagent analysis both indicate that "OPD for safety" is too weak and likely to collide with existing work.

Impact: first-stage docs and Pro questions focus on reconciliation ability, judgment deltas, action modes, and fork preservation.

## 2026-06-30 - Keep credentials out of tracked Git

Decision: write credentials into `.secrets/PROJECT_CREDENTIALS.md`, but keep `.secrets/` ignored by Git.

Reason: the user asked for credentials to be documented but not shown in conversation. Pro and Git progress sharing do not require exposing them.

Impact: tracked docs mention the private credential file location but not its content.

