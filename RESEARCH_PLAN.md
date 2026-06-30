# Research Plan

## Working Title

Reconcile-OPSD: Fork-Preserving Judgment-Delta Self-Distillation for Reasoning Safety

## Core Question

How can we distill safety-relevant judgment improvements into reasoning models under conflicting or ambiguous scenarios, while preserving their ability to explore alternatives, backtrack, express uncertainty, and avoid premature convergence?

## What This Is Not

- Not simply OPD on safety prompts.
- Not full CoT KL imitation.
- Not refusal-style distillation.
- Not a replacement for safety policy definition.

## Target Capability

Reconciliation ability: the ability to coordinate user intent, helpfulness, risk, constraints, uncertainty, evidence strength, and response mode during long-chain reasoning.

Relevant action modes:

- direct answer;
- ask clarification;
- safe high-level explanation;
- safe redirect;
- partial allowed assistance;
- refusal with brief reason;
- continue reasoning or verification.

## Proposed Method Sketch

1. Student rollout: let the student generate under the normal user prompt.
2. Same-prefix teachers:
   - `T0`: same/base teacher without reconciliation context.
   - `Tr`: teacher with reconciliation scaffold, policy/risk context when available, and allowed assistance boundary.
3. Judgment delta:
   - Estimate how reconciliation context changes the teacher distribution or action-mode judgment.
   - Distill the delta rather than the whole teacher distribution or full teacher CoT.
4. Fork-preserving adaptation:
   - Use stronger pressure on confident action-decision states.
   - Use weaker or entropy-preserving objectives on high-uncertainty fork states.
   - Use higher weight on drift states where a trajectory moves from safe judgment into unsafe or over-refusal behavior.
5. Auxiliary action-mode distillation:
   - Learn structured response mode decisions without forcing the final model to expose training-only labels.

## First-Stage Research Contributions

1. Define reconciliation ability as the target object for reasoning safety.
2. Show why naive privileged self-OPD can improve safety bias while risking fork suppression, premature refusal, or reduced uncertainty.
3. Propose judgment-delta distillation to reduce style, length, and refusal-prior contamination.
4. Propose fork-preserving adaptive OPD for high-entropy reasoning states.
5. Evaluate both final safety behavior and reasoning-process preservation.

## MVP Experiment Plan

### Phase 0: Setup and Literature Collision Scan

- Create repo, docs, and Pro collaboration workflow.
- Ask Pro to search for collisions around judgment delta, fork-preserving safety distillation, action-mode distillation, and reconciliation ability.
- Decide the exact first contribution claim after the collision scan.

### Phase 1: Data Schema and Seed ReconcileBench

Create a small seed dataset with fields:

- `prompt`
- `scenario_type`
- `risk_category`
- `benign_allowed_parts`
- `disallowed_parts`
- `initial_judgment`
- `revised_judgment`
- `judgment_delta`
- `action_mode`
- `forks_to_keep`
- `forks_to_prune`
- `final_response`

Scenario types:

- clear harmful;
- benign-sensitive;
- dual-use;
- ambiguous intent;
- long-context distraction;
- non-safety judgment under uncertainty.

### Phase 2: Baseline Evaluation

Evaluate base models on:

- harmful compliance;
- over-refusal;
- clarification accuracy;
- safe-completion quality;
- action-mode accuracy;
- deliberation drift;
- fork/backtracking/uncertainty markers;
- general reasoning benchmarks where feasible.

### Phase 3: Smoke Training

Use a small model and LoRA-style training to validate:

- data formatting;
- action-mode objective;
- evaluation harness;
- logging;
- checkpoint save/load.

Candidate smoke models:

- `/data/LLM/Qwen3-8B`
- `/data/LLM/Qwen3-30B-A3B` if resource conditions allow

Use `/data/LLM/Qwen2.5-7B-Instruct` as a non-thinking instruct baseline, not as the primary thinking-model smoke target. Use `/data/LLM/YuFeng-XGuard-Reason-8B` only after confirming it behaves as a generative reasoning model rather than only a safety classifier/judge.

### Phase 4: Judgment-Delta Prototype

Implement same-prefix teacher scoring and compare:

- base;
- deliberative SFT;
- naive privileged self-OPD;
- judgment-delta self-OPD;
- fork-preserving judgment-delta self-OPD.

### Phase 5: High-VRAM Main Run

Run at least one >70GB VRAM experiment using:

- `/data/LLM/Qwen3-30B-A3B-Thinking`, or
- `/data/LLM/Qwen3-Next-80B-A3B-Thinking`, or
- `/data/LLM/Llama-3.3-70B-Instruct` with QLoRA/LoRA as a non-thinking large baseline.

Do not start until GPU availability and dependencies are checked.

## Questions for ChatGPT Pro

1. Which OPD/OPSD/self-distillation papers use full CoT KL, and which use final answer, preference, process, or logit-level signals?
2. Is there existing work explicitly named judgment delta, reasoning delta, critique delta, correction distillation, or similar?
3. What safety-reasoning work already studies ambiguous harmful intent, dual-use requests, over-refusal, and helpful refusal together?
4. Is there prior safety distillation work that explicitly preserves reasoning forks, backtracking, or uncertainty?
5. Is reconciliation ability already named as conflict resolution, constraint reconciliation, preference reconciliation, or safety-helpfulness tradeoff reasoning?
6. Which benchmarks can measure harmful compliance, over-refusal, clarification, safe completion, and deliberation drift?
7. What is the strongest ablation matrix for proving this is not just safe SFT or safe OPD?
8. What is the minimum credible model/data/benchmark setup for a 1-2 month first result?
