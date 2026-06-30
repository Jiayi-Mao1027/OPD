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
High-VRAM target experiments should actually use more than 70GB GPU memory.
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

No DeepSeek-R1-Distill-Qwen model was found locally.

## Proposed MVP

1. Literature collision scan.
2. Seed ReconcileBench schema.
3. Baseline evaluation on harmful, benign-sensitive, dual-use, ambiguous, long-context distraction, and non-safety uncertainty tasks.
4. LoRA smoke training on Qwen2.5-7B, Qwen3-8B, or YuFeng-XGuard-Reason-8B.
5. Judgment-delta same-prefix teacher prototype.
6. 32B-class high-VRAM run after the method is stable.

## Specific Questions

1. Which existing papers most threaten the novelty of judgment-delta self-distillation?
2. Has anyone explicitly preserved reasoning forks/backtracking/uncertainty during safety distillation?
3. What should be the exact contribution claim if we want to avoid being seen as safe SFT, safe OPD, or process supervision?
4. Which benchmarks can measure harmful compliance, over-refusal, clarification accuracy, safe completion, deliberation drift, and fork preservation?
5. What is the strongest minimal ablation matrix?
6. Should the first smoke model be Qwen2.5-7B-Instruct, Qwen3-8B, or YuFeng-XGuard-Reason-8B?
7. If no R1-Distill model is local, is it worth downloading DeepSeek-R1-Distill-Qwen-14B/32B for the first phase?

