# Pro Review Packet: Pairwise Compactscore Interpretation

Use this packet when asking ChatGPT Pro to review the current Reconcile-OPSD
pairwise stage. Do not include credentials or server tokens.

## Project Context

Repository: `https://github.com/Jiayi-Mao1027/OPD`

Current commit: `f54b557 eval: add compactscore alignment diagnostics`

Working direction: Reconcile-OPSD / fork-preserving judgment-delta
self-distillation for safety boundary decisions. First-stage experiments use
Qwen3-8B as the thinking-capable student model.

Current hard training policy:

- no full-parameter fine-tuning;
- no QLoRA for first-stage pairwise runs;
- rank-128 LoRA only;
- control memory with `batch_size`, `gradient_accumulation_steps`, and
  `max_length`;
- R1 / DeepSeek-R1-Distill deferred.

## Current Result

Data:

- train: `data/pairwise/reconcilebench_v0_1_train_pairwise_posbalanced.jsonl`
- original dev: `data/pairwise/reconcilebench_v0_1_dev_pairwise.jsonl`
- position-balanced dev:
  `data/pairwise/reconcilebench_v0_1_dev_pairwise_posbalanced.jsonl`

Runs:

- `r128_lr1e5`: rank-128 LoRA, compact target, max length 1536, 24 steps,
  grad accum 8, lr `1e-5`, no 4-bit loading.
- `r128_lr3e6_len1024`: rank-128 LoRA, compact target, max length 1024,
  24 steps, grad accum 16, lr `3e-6`, no 4-bit loading.

Winner-only scoring:

- Original dev:
  - full BF16 base: `22/28`, fork `1/3`, scope `11/13`, refusal `5/5`
  - `r128_lr1e5`: `23/28`, fork `2/3`, scope `11/13`, refusal `4/5`
  - `r128_lr3e6_len1024`: `23/28`, fork `2/3`, scope `11/13`,
    refusal `4/5`
- Position-balanced dev:
  - full BF16 base: `44/56`, fork `4/6`, scope `21/26`, refusal `10/10`,
    pred A/B `36/20`, swap consistency `18/28`, gate fail
  - `r128_lr1e5`: `44/56`, fork `5/6`, scope `19/26`, refusal `8/10`,
    pred A/B `28/28`, swap consistency `18/28`, gate fail
  - `r128_lr3e6_len1024`: `43/56`, fork `5/6`, scope `19/26`,
    refusal `9/10`, pred A/B `29/27`, swap consistency `19/28`, gate fail

Compact structured scoring:

- `score-mode=compact_structured_judgment` scores the full compact training
  target: `WINNER`, `GOLD_ACTION`, `HARD_AXIS`, `DELTA_TAG`, and optional
  scope/granularity/fork-policy fields.
- Under this mode, both rank-128 adapters reach `28/28` on original dev and
  `56/56` on position-balanced dev.
- This is label-conditioned because the scored continuation includes gold
  metadata fields from the pair record.

Parent-level swap diagnostics:

- `lr1e-5`: 10 inconsistent parents out of 28.
- `lr3e-6_len1024`: 9 inconsistent parents out of 28.
- Failures concentrate in `scope_contract / wrong_scope`, especially
  `unsafe_specificity`.
- This looks more like position-invariant pairwise judgment instability than a
  simple A/B side collapse.

## Current Interpretation

Main metric should remain `score-mode=winner_only`.

`compact_structured_judgment` should be treated as an auxiliary target-alignment
diagnostic only. It confirms that the adapter learned the compact target format,
but it should not override a failed winner-only swap-consistency gate and should
not be claimed as proof of safer generated assistant behavior.

Current claim should be conservative:

> Rank-128 non-QLoRA LoRA on position-balanced data can learn the compact
> judgment-delta target and reduce simple candidate-side collapse. Under
> winner-only scoring it improves fork-state on the original dev slice, but
> position-balanced swap consistency remains below gate and scope/refusal
> regressions remain unresolved.

## Questions For Pro

1. Is the primary/auxiliary metric split above correct, or is there a better
   way to use compact structured logprob scoring without label leakage?
2. Should the next validation be greedy compact-target generation parsing,
   a newly held-out fork/scope pairwise set, external/human audit of
   assistant-facing responses, or a paired-consistency training objective?
3. For the next run, should we avoid more LoRA steps and instead fix the
   evaluation/generation path first?
4. What contribution framing remains defensible at this point?

