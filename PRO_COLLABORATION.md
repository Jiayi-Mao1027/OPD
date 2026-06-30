# ChatGPT Pro Collaboration Protocol

## Role Split

Codex owns:

- remote execution;
- project files;
- experiment commands;
- environment changes;
- Git commits;
- logs and reproducibility.

ChatGPT Pro owns:

- research framing;
- literature collision checks;
- contribution sharpening;
- benchmark suggestions;
- ablation critique;
- risk analysis.

Git owns:

- accepted project facts;
- current plan;
- decisions;
- experiment evidence.

## Workflow

1. Codex gathers current repo state and experiment evidence.
2. Codex prepares a sanitized context packet.
3. User sends the packet to ChatGPT Pro, or Codex interacts with the open Pro chat when explicitly instructed.
4. Pro gives research advice.
5. Codex summarizes accepted advice into tracked docs.
6. Codex executes only after checking paths, environment, GPU state, and risk.
7. Codex logs and commits the result.

## What To Send Pro

Send:

- current goal;
- current repo state;
- concise research background;
- accepted decisions;
- non-sensitive environment/model inventory;
- metrics and failure summaries;
- specific questions.

Do not send:

- tokens;
- passwords;
- private keys;
- cookies;
- raw `.env`;
- raw service headers;
- unreviewed generated code that should not influence the repo.

## Context Packet Template

```md
# OPD Safety Research Context Packet

## Current Goal

...

## Project Background

Project: Reconcile-OPSD / Fork-Preserving Judgment-Delta Self-Distillation.
Codex executes engineering and experiments.
ChatGPT Pro provides research planning and critique.
Git is the shared progress layer.

## Current Repo State

Branch:

```text
...
```

Latest commit:

```text
...
```

Working tree:

```text
...
```

## Current Progress

Done:

- ...

Blocked:

- ...

Next:

- ...

## Evidence

Model paths:

```text
...
```

GPU summary:

```text
...
```

Experiment result summary:

```text
...
```

## What I Need From Pro

Please answer:

1. ...
2. ...
3. ...

## Constraints

- Do not ask for or include secrets.
- Treat Pro suggestions as research advice.
- If proposing experiments, include expected memory, failure criteria, and minimal validation.
```

## Advice Intake Template

```md
## Pro Advice Intake

Date:
Question asked:
Key recommendations:
Accepted actions:
Rejected or deferred actions:
Risks:
Files to update:
Experiments to run:
```

