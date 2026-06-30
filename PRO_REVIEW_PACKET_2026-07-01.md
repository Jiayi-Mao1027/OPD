# Pro Review Packet: Pairwise Compact Generation Result

Use this packet when asking ChatGPT Pro to review the current Reconcile-OPSD
pairwise stage. Do not include credentials or server tokens.

## Project Context

Repository: `https://github.com/Jiayi-Mao1027/OPD`

Review baseline commit: `83cf7c1 eval: add compact generation parsing`, plus
the later mismatch-analysis commit that updates this packet.

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

Greedy compact generation:

- Script: `scripts/generate_pairwise_compact_judgments.py`
- Summary report: `reports/pairwise_v0_1_compact_generation_summary.md`
- Original dev:
  - full BF16 base: `23/28 = 0.8214`, fork `1/3`, scope `11/13`
  - `r128_lr1e5`: `20/28 = 0.7143`, fork `1/3`, scope `9/13`
  - `r128_lr3e6_len1024`: `22/28 = 0.7857`, fork `1/3`, scope `11/13`
- Position-balanced dev:
  - full BF16 base: `43/56 = 0.7679`, fork `4/6`, scope `20/26`,
    pred A/B `31/25`, swap consistency `19/28 = 0.6786`, gate fail
  - `r128_lr1e5`: `39/56 = 0.6964`, fork `4/6`, scope `17/26`,
    pred A/B `19/37`, swap consistency `15/28 = 0.5357`, gate fail
  - `r128_lr3e6_len1024`: `42/56 = 0.7500`, fork `4/6`,
    scope `19/26`, pred A/B `28/28`, swap consistency `18/28 = 0.6429`,
    gate fail
- Full compact-target match is `0.0000` for all generation runs.
- `r128_lr1e5` has higher compact field accuracy, but lower winner accuracy,
  worse scope accuracy, and worse position-balanced consistency.
- `r128_lr3e6_len1024` is closer to base and avoids strong side skew, but it
  still does not beat base or pass the position-balanced gate.

Raw-generation mismatch analysis:

- Script: `scripts/analyze_compact_generation_mismatches.py`
- Report: `reports/pairwise_v0_1_compact_generation_mismatch_analysis.md`
- Full target exact match is too strict as a standalone behavioral metric, but
  it is useful as a schema diagnostic.
- Base and `r128_lr3e6_len1024` average only `2.00` parsed fields: mostly
  `WINNER` plus `DELTA_TAG`. The generated `DELTA_TAG` often looks like a
  `GOLD_ACTION` value such as `safe_redirect`, `direct_answer`, or
  `safe_high_level`.
- `r128_lr1e5` averages about `6.9` parsed fields and has high present-field
  rate, so it learned to emit the compact shape. It still has `0.0000` full
  match because `HARD_AXIS`, `DELTA_TAG`, and `SCOPE_ERROR_DIRECTION` are
  schema-confused. Common examples: `HARD_AXIS: scope` for
  `scope_contract`, `DELTA_TAG: scope_error_direction`, and
  `SCOPE_ERROR_DIRECTION: over/over_scope`.
- This points to target/prompt/label-ontology redesign before more rank-128
  LoRA steps on the same compact target.

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

The generation check strengthens the conservative interpretation:

> The compactscore result was optimistic/label-conditioned. Under greedy
> compact generation, current rank-128 LoRA does not beat full BF16 Qwen3-8B
> base on winner accuracy, scope accuracy, or position-balanced swap
> consistency.

Previous conservative winner-only claim:

> Rank-128 non-QLoRA LoRA on position-balanced data can learn the compact
> judgment-delta target and reduce simple candidate-side collapse. Under
> winner-only scoring it improves fork-state on the original dev slice, but
> position-balanced swap consistency remains below gate and scope/refusal
> regressions remain unresolved.

Updated claim:

> Current rank-128 compact LoRA is not yet a positive method result. It is a
> useful diagnostic showing that compact target alignment does not
> automatically transfer to stronger generated pairwise judgment. Mismatch
> analysis suggests the current compact target asks for too many unsupported
> gold metadata fields and needs a clearer label ontology.

## Questions For Pro

1. Given the negative greedy generation result, is there any defensible way to
   use compact structured logprob scoring beyond target-alignment diagnostics?
2. Should the compact target be reduced to `WINNER` plus one or two observable
   rationale tags, or should the prompt explicitly include the label ontology
   and ask for full metadata prediction?
3. Should the next validation be a fresh held-out fork/scope pairwise set,
   external/human audit of assistant-facing responses, or a paired-consistency
   training objective?
4. What contribution framing remains defensible if current rank-128 LoRA does
   not beat full BF16 base?
