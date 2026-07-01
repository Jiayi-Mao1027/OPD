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

## 2026-07-01 - Use fresh fork/scope heldout as a diagnostic, not a benchmark

Decision: use `data/heldout/reconcilebench_v0_fork_scope_holdout.jsonl` and its v0.1 pairwise derivatives as a fresh fork/scope diagnostic set.

Reason: the existing dev split had already shaped model/target decisions. A separate heldout slice is needed to check whether the pairwise signal survives outside the current dev set.

Impact: heldout results can support or reject a narrow fork/scope claim, but should not be described as a full safety benchmark. The set is small, Chinese-only, and does not cover every source action mode.

## 2026-07-01 - Do not retroactively relabel historical pairwise rendering

Decision: fix `render_card` newlines for newly generated pairwise data, but do not regenerate historical train/dev pairwise files inside the current result narrative.

Reason: the earlier train/dev pairwise files and all existing adapters were produced with the old concatenated decision-field rendering. Regenerating them now would create a new experimental surface and blur which inputs produced the current adapters.

Impact: fresh heldout files use the fixed rendering. Historical train/dev results remain valid as their own logged artifacts, but must carry the old-rendering caveat.

## 2026-07-01 - Pivot to candidate-local reconciliation scoring

Decision: freeze the current compact pairwise generation, boundary-plan prompt bridge, and 38-example final-response SFT lines as negative diagnostics. The next main method path is a candidate-local constrained scorer that predicts `ACCEPTABLE` and one observable `ERROR_TAG` for each candidate independently.

Reason: the latest response-level SFT and boundary-plan bridge do not transfer the pairwise signal to assistant-facing final responses. ChatGPT Pro reviewed the compact, heldout, response-level SFT, and boundary-bridge evidence and advised that the current result is diagnostic rather than method success. Pro also warned that generic "OPD for safety" and "reasoning safety beyond refusal" framing collides with prior OPSD/OPCD/OPSA, deliberative safety reasoning, RATIONAL-style safety reasoning, trace-safety, generic pairwise preference learning, and judge position-bias work.

Impact: do not claim Reconcile-OPSD improves assistant-facing safety behavior yet. First build and evaluate v0.2 candidate-local data, induce pairwise winners from independent candidate scores, and require strict fresh heldout winner/swap gates before treating the scorer as a method signal. Assistant-facing transfer should be tested through response selection against greedy fullbase before any renewed generator distillation.

