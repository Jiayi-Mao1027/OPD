# AGENTS.md

## Project Context

This is an OPD safety research project focused on Reconcile-OPSD: fork-preserving judgment-delta self-distillation for reasoning models.

Execution agent: Codex.
Research planning and advice: ChatGPT Pro.
Progress sharing layer: Git.
Remote project root: `/data03/liang/mjy/reconcile_opsd`.
Conda environment: `mjy`.
Model root: `/data/LLM`.

## Hard Rules

- Read this file first before doing project work.
- Treat Git-tracked files as the shared source of truth for project progress.
- Treat ChatGPT Pro output as research advice, not executable ground truth.
- Do not let Pro text directly overwrite code, configs, prompts, or experiment scripts.
- Do not overwrite or repurpose `/data03/liang/mjy/safe_opd`; it is an older separate project.
- Verify actual model paths under `/data/LLM` before using a model.
- Do not assume DeepSeek or other models exist unless the path is verified.
- Do not run long or GPU-heavy jobs without checking `nvidia-smi` first.
- Do not kill or displace existing GPU processes without explicit user approval.
- For high-memory target experiments, expected and observed GPU memory occupation should exceed 70GB.
- If a high-memory run uses less than 70GB, mark the run as suspect and investigate model size, precision, sharding, sequence length, batch size, and device placement.
- Keep credentials in `.secrets/PROJECT_CREDENTIALS.md` or environment variables. Do not paste them into conversation replies.
- Do not commit `.secrets/`, `.env*`, model checkpoints, raw model weights, or large generated outputs.

## Work Start Checklist

1. Check `git status --short --branch`.
2. Read `PROJECT_STATUS.md`, `TODO.md`, `DECISIONS.md`, and recent `EXPERIMENT_LOG.md`.
3. Determine whether the current task is planning, implementation, experiment execution, or analysis.
4. If remote/GPU work is needed, check `nvidia-smi` and record the relevant state.
5. If Pro input is needed, prepare a sanitized context packet from tracked docs and current evidence.

## GPU Rules

- Record GPU model, count, visible devices, memory usage, and running processes before major runs.
- Record expected memory and actual peak memory in `EXPERIMENT_LOG.md`.
- Prefer smoke tests on smaller models before high-VRAM experiments.
- For 70GB+ target runs, prefer 32B LoRA/QLoRA or 70B QLoRA class experiments.
- Do not pad or cache merely to inflate memory usage; also track utilization, tokens/sec, and loss behavior.

## Pro Interaction Rules

- Send Pro concise context packets, not raw working directories.
- Ask Pro research questions: novelty, literature collisions, benchmark design, contribution framing, ablation logic, and risk analysis.
- Do not send Pro secrets, tokens, passwords, cookies, private keys, or raw service responses containing sensitive data.
- After receiving Pro advice, summarize it into `RESEARCH_PLAN.md`, `DECISIONS.md`, `TODO.md`, or `PROJECT_STATUS.md`.
- Mark Pro-derived statements as hypotheses or recommendations until verified.

## Git Rules

- Commit small, meaningful units of work.
- Use clear prefixes: `docs:`, `plan:`, `exp:`, `code:`, `fix:`, `config:`, `log:`, `analysis:`.
- Keep code/config changes separate from experiment results where practical.
- Commit failed experiment logs when they contain useful evidence.
- Do not rewrite shared history unless explicitly requested.

