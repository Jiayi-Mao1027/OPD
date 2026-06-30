# Pro Review Packet: v0 QLoRA Negative Result

Use this packet for ChatGPT Pro research/planning review. It contains no credentials or private tokens.

## Current Git State

Repository: `https://github.com/Jiayi-Mao1027/OPD`

Latest pushed commit after the v0 run:

```text
46d8406 exp: log qwen3 v0 qlora result
```

Remote project path:

```text
/data03/liang/mjy/reconcile_opsd
```

## Project Direction

Working thesis:

> Distill safety-relevant judgment improvements into reasoning models under conflicting or ambiguous scenarios, while preserving exploration, backtracking, uncertainty expression, and useful reasoning forks.

The intended contribution is not refusal-only safety. Current framing candidates:

- Reconcile-OPSD
- Fork-Preserving Judgment-Delta Self-Distillation
- action-mode distillation without full CoT imitation

## Data

`data/reconcilebench_v0.jsonl` has 52 synthetic/seed-quality examples.

Action-mode counts:

```text
ask_clarification: 8
continue_reasoning: 9
direct_answer: 7
partial_allowed: 7
refuse: 7
safe_high_level: 7
safe_redirect: 7
```

Fixed split:

```text
train: 38 examples
dev: 14 examples
dev has exactly 2 examples per action mode
```

Label guide:

```text
docs/action_mode_label_guide.md
```

## Models And Constraints

First-stage model:

```text
/data/LLM/Qwen3-8B
```

Qwen3-8B template supports thinking mode, and a smoke run with `--enable-thinking` emitted `<think>`. Current action-mode classifier experiments deliberately use `enable_thinking=False` for comparability and do not train explicit thinking traces.

R1 experiments are deferred. Prefer 8B or smaller models first.

## Current Training Target

Training prompt asks for:

```text
ACTION_MODE: <one mode>
REASON: <one short reason>
```

Target text is:

```text
ACTION_MODE: {example.action_mode}
REASON: {example.judgment_delta}
```

This may be part of the problem: `judgment_delta` is heterogeneous and sometimes too phrase-like for stable generation.

## Key Results

Seed baseline:

```text
Qwen3-8B base on 12 seed examples:
action_mode_accuracy = 0.1667
collapse pattern = mostly refuse / safe_high_level
```

2-step smoke:

```text
QLoRA on 4 seed examples for 2 steps:
loss = 5.6548 -> 3.3280
seed eval adapter = 0.1667
base 4-bit control = 0.1667
```

v0 dev base control:

```text
4-bit Qwen3-8B base on v0 dev with train prompt:
total = 14
action_mode_accuracy = 0.4286
predicted_counts = safe_high_level: 7, refuse: 5, direct_answer: 2
```

v0 QLoRA 20-step:

```text
train = data/splits/reconcilebench_v0_train.jsonl
dev = data/splits/reconcilebench_v0_dev.jsonl
max_steps = 20
loss = 5.9287 -> 1.7881
dev action_mode_accuracy = 0.3571
predicted_counts = safe_high_level: 4, ask_clarification: 3, safe_redirect: 4, direct_answer: 2, refuse: 1
peak allocated CUDA memory = 9354.79 MB
```

Observed issue:

- The adapter predicts a broader action-mode distribution than the base control.
- Dev accuracy is lower than the base control.
- Several generated `REASON` fields repeat phrases, suggesting the current generation target is unstable.
- Longer training is not justified until target/data/eval design is fixed.

Follow-up normalized-reason run:

```text
target_style = normalized_reason
max_steps = 20
loss = 3.2749 -> 0.5582
dev action_mode_accuracy = 0.4286
predicted_counts = partial_allowed: 3, safe_redirect: 6, direct_answer: 4, refuse: 1
```

Interpretation of follow-up:

- Normalized reasons remove most repetitive reason generation.
- The adapter recovers to the 4-bit base control accuracy but does not exceed it.
- It still fails `ask_clarification` and `continue_reasoning` on dev, often mapping them to `safe_redirect` or `partial_allowed`.
- This points toward response-level evaluation and/or classification-style fork/judgment targets rather than longer SFT on the same target.

## Questions For Pro

1. Is action-mode SFT too weak to support the Reconcile-OPSD contribution, even after normalized reasons stabilize generation?
2. Should the next target be:
   - shorter normalized action-mode reasons,
   - response-level distillation using `final_response`,
   - pairwise judgment-delta classification,
   - fork-state prediction using `forks_to_keep/prune`,
   - or a different ablation?
3. How should we separate method signal from synthetic-label noise in a 52-example first-stage dataset?
4. What minimal dev metrics should be added before more QLoRA runs: response safety/usefulness, harmful compliance, over-refusal, clarification accuracy, safe completion, deliberation drift, fork preservation?
5. How should thinking mode be incorporated: keep action-mode classifier thinking-off, add a separate thinking-on response eval, or train a small explicit fork-preservation target?
6. What is the strongest contribution framing given these early results?
7. Which literature or benchmarks most threaten novelty for this framing?

## Suggested Next Engineering Move

Do not simply increase training steps. First add one of:

- a normalized short-reason target builder;
- a response-level `final_response` generation/eval path;
- a pairwise or classification-style judgment-delta target;
- a label-audit pass to identify ambiguous or inconsistent v0 examples.
