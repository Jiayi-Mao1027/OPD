# OPD Safety Research Context Packet

## Current Goal

Please help refine the first-stage research plan for a project currently called Reconcile-OPSD / Fork-Preserving Judgment-Delta Self-Distillation.

Focus on:

1. novelty and collision risk;
2. strongest contribution framing;
3. first credible benchmark/evaluation design;
4. minimum viable ablation matrix;
5. model choices for 1-2 month feasibility.

## Project Background

The project is about OPD safety for reasoning models, but it should not be framed as simple "safe OPD".

Working thesis:

> Distill safety-relevant judgment improvements into reasoning models under conflicting or ambiguous scenarios, while preserving exploration, backtracking, uncertainty expression, and useful reasoning forks.

Core concepts:

- reconciliation ability;
- judgment-delta self-distillation;
- fork-preserving adaptive OPD;
- action-mode distillation;
- avoid full CoT KL imitation.

## Current Engineering Context

Codex handles remote execution and experiments.
ChatGPT Pro provides research planning and critique.
Git is the shared progress layer.

Remote project root:

```text
/data03/liang/mjy/reconcile_opsd
```

Conda environment:

```text
/data/conda/envs/mjy
```

Model root:

```text
/data/LLM -> /data01/LLM
```

GPU:

```text
4 x NVIDIA H100 PCIe, about 79GB each
```

Important constraint:

```text
First-stage experiments should prefer 8B or smaller models. High-VRAM target experiments should eventually use more than 70GB GPU memory, but only after the small-model loop is stable.
```

## Verified Local Models

```text
/data/LLM/Qwen2.5-7B-Instruct
/data/LLM/Qwen2.5-14B-Instruct
/data/LLM/Qwen2.5-32B-Instruct
/data/LLM/Qwen3-8B
/data/LLM/Qwen3-30B-A3B-Thinking
/data/LLM/Qwen3-Next-80B-A3B-Thinking
/data/LLM/Llama-3.1-8B-Instruct
/data/LLM/Llama-3.3-70B-Instruct
/data/LLM/YuFeng-XGuard-Reason-8B
/data/LLM/Meta-SecAlign-8B
/data/LLM/Meta-SecAlign-70B
```

No DeepSeek-R1-Distill-Qwen model was found locally. R1-style experiments are deferred for the first stage.

## Proposed MVP

1. Literature collision scan.
2. Seed ReconcileBench schema.
3. Baseline evaluation on harmful, benign-sensitive, dual-use, ambiguous, long-context distraction, and non-safety uncertainty tasks.
4. LoRA smoke training on Qwen3-8B as the default thinking candidate, with Qwen2.5-7B-Instruct only as a non-thinking baseline.
5. Judgment-delta same-prefix teacher prototype.
6. 32B-class high-VRAM run after the method is stable.

## Latest Engineering Evidence

- Qwen3-8B chat template supports thinking mode; a short smoke with `--enable-thinking` emitted `<think>`.
- The current action-mode eval prompt runs with explicit `ACTION_MODE` output and thinking disabled for classifier-style comparability.
- Seed ReconcileBench currently has 12 examples across harmful, benign-sensitive, dual-use, ambiguous, long-context distraction, and non-safety uncertainty cases.
- Base Qwen3-8B action-mode baseline on the 12 seed examples: `0.1667` accuracy, mostly collapsing to `refuse` or `safe_high_level`.
- A 4-bit QLoRA smoke trained Qwen3-8B for 2 steps on 4 seed examples and saved a PEFT adapter successfully.
- Adapter-aware eval is now wired: same 4-bit base, same train prompt, same 12 seed examples. The 2-step smoke adapter also gets `0.1667`, so it proves the training/eval loop, not quality.
- A label guide now exists at `docs/action_mode_label_guide.md`; current priority is expanding data, fixing a train/dev split, and auditing taxonomy boundaries before longer training.
- ReconcileBench v0 now has 52 synthetic/seed-quality examples. Action-mode counts are: `continue_reasoning: 9`, `ask_clarification: 8`, and `direct_answer`, `partial_allowed`, `refuse`, `safe_high_level`, `safe_redirect` each at `7`.
- The fixed v0 split has 38 train and 14 dev examples; dev has exactly two examples per action mode.
- Qwen3-8B 4-bit base control on v0 dev with the train prompt gets `0.4286` action-mode accuracy. Predicted counts: `safe_high_level: 7`, `refuse: 5`, `direct_answer: 2`.
- A 20-step QLoRA run on v0 train drops train loss `5.9287 -> 1.7881`, but v0 dev accuracy falls to `0.3571`. Predicted counts: `safe_high_level: 4`, `ask_clarification: 3`, `safe_redirect: 4`, `direct_answer: 2`, `refuse: 1`.
- The adapter learned a broader label distribution but produced repetitive reason text and did not improve dev accuracy. This suggests the next step should not be simply more steps.
- A normalized-reason target avoids most repetitive reason generation and recovers dev accuracy to `0.4286`, matching the 4-bit base but still not beating it. It still misses `ask_clarification` and `continue_reasoning`, often mapping them to `safe_redirect` or `partial_allowed`.
- Response-level evaluation and judgment-delta/fork metrics remain missing.

## Specific Questions

1. Which existing papers most threaten the novelty of judgment-delta self-distillation?
2. Has anyone explicitly preserved reasoning forks/backtracking/uncertainty during safety distillation?
3. What should be the exact contribution claim if we want to avoid being seen as safe SFT, safe OPD, or process supervision?
4. Which benchmarks can measure harmful compliance, over-refusal, clarification accuracy, safe completion, deliberation drift, and fork preservation?
5. What is the strongest minimal ablation matrix?
6. Should the first smoke model be Qwen2.5-7B-Instruct, Qwen3-8B, or YuFeng-XGuard-Reason-8B?
7. Given the first-stage preference for 8B or smaller thinking models, what is the strongest small-model experimental setup?
8. Given the v0 negative result, should the next target be shorter normalized action-mode reasons, response-level distillation, pairwise judgment-delta classification, or a different ablation?
9. How should we separate a real method signal from synthetic-label noise in a 52-example first-stage dataset?
