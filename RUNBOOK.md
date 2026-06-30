# Runbook

## Connect

Use SSH to connect to `10.26.128.46`. The working project directory is:

```bash
cd /data03/liang/mjy/reconcile_opsd
```

Use the conda environment:

```bash
/data/conda/bin/conda run -n mjy python -V
```

For interactive shell sessions:

```bash
source /data/conda/etc/profile.d/conda.sh
conda activate mjy
```

CUDA extension environment:

```bash
export CUDA_HOME=/usr/local/cuda-12.2
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}
```

Use those exports before deepspeed or flash-attn related runs.

Common defaults for paths, CUDA, GPU policy, Qwen3-8B evaluation, proxy
recovery, and GitHub checks are also recorded in `docs/common_configs.md`.

Server proxy for GitHub/network operations:

```bash
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
export HTTP_PROXY=$http_proxy
export HTTPS_PROXY=$https_proxy
export no_proxy=localhost,127.0.0.1,::1
```

## Standard Checks

Git:

```bash
git status --short --branch
git log --oneline -5
```

GPU:

```bash
nvidia-smi
nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu --format=csv
nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_memory --format=csv
python scripts/gpu_status.py
python scripts/gpu_status.py --export
```

The project GPU helper selects a device with at least `20000 MB` free and at most
`70000 MB` already used by default. Override with `--min-free-mb` and
`--max-used-mb` only when the reason is logged.

Models:

```bash
find -L /data/LLM -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | sort
```

Model template check:

```bash
python3 - <<'PY'
import json, pathlib, re
model = pathlib.Path("/data/LLM/Qwen3-8B")
tok = json.loads((model / "tokenizer_config.json").read_text(errors="replace"))
cfg = json.loads((model / "config.json").read_text(errors="replace"))
tmpl = tok.get("chat_template") or ""
print("model_type:", cfg.get("model_type"))
print("architectures:", cfg.get("architectures"))
print("has_chat_template:", bool(tmpl))
print("template_mentions_thinking:", bool(re.search(r"think|reason|thinking|enable_thinking", tmpl, re.I)))
print("template_preview:", " ".join(tmpl.split())[:500])
PY
```

Environment packages:

```bash
/data/conda/bin/conda run -n mjy python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.device_count())"
```

Installed training dependencies:

```bash
source /data/conda/etc/profile.d/conda.sh
conda activate mjy
export CUDA_HOME=/usr/local/cuda-12.2
export PATH=$CUDA_HOME/bin:$PATH
python - <<'PY'
import importlib.metadata as md
for p in ["bitsandbytes", "deepspeed", "flash-attn", "packaging"]:
    try:
        print(f"{p}=={md.version(p)}")
    except md.PackageNotFoundError:
        print(f"{p}=MISSING")
PY
```

## Logging Required For Experiments

Before an experiment, add an `EXPERIMENT_LOG.md` entry with:

- date/time;
- Git commit;
- branch;
- model path;
- dataset/input;
- command;
- expected GPU memory;
- GPU state before run.

After an experiment, update the entry with:

- actual peak memory;
- GPU state during/after;
- result metrics;
- failure reason if any;
- next action.

## 70GB+ Rule

High-VRAM target experiments must exceed 70GB actual GPU memory usage. If they do not:

1. Check whether the intended model was actually loaded.
2. Check precision and quantization.
3. Check tensor parallel / device map.
4. Check sequence length and micro batch size.
5. Check whether gradient checkpointing, LoRA, or CPU offload changed memory usage.
6. Mark the result as suspect until explained.

For first-stage 8B LoRA and evaluation runs, use the inverse safety rule:
avoid devices that already have more than `70000 MB` used, and log the selected
device before starting. The helper script enforces this default policy.

## Standard v0 QLoRA Runner

This is a frozen legacy baseline path. Do not use QLoRA for the current
pairwise rank-128 stage.

Use this wrapper for reproducible Qwen3-8B v0 action-mode runs:

```bash
TARGET_STYLE=normalized_reason MAX_STEPS=20 scripts/run_qwen3_v0_qlora.sh
```

Common overrides:

```bash
TARGET_STYLE=judgment_delta OUTPUT_DIR=outputs/train_v0/qwen3_8b_action_lora_steps20 scripts/run_qwen3_v0_qlora.sh
MIN_FREE_MB=20000 MAX_USED_MB=70000 scripts/run_qwen3_v0_qlora.sh
```

Current reference configs:

```text
configs/qwen3_8b_v0_judgment_delta_steps20.json
configs/qwen3_8b_v0_normalized_reason_steps20.json
```

## Constrained Scoring And Audit

Use this path after the current v0 action-mode/REASON SFT negative results.
It scores candidate labels directly instead of asking the model to generate a
free-form `ACTION_MODE + REASON` response.

Base control:

```bash
eval "$(python scripts/gpu_status.py --export)"
python scripts/score_action_modes.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/splits/reconcilebench_v0_dev.jsonl \
  --output outputs/scores/qwen3_8b_v0_dev_base_trainprompt_4bit.jsonl \
  --load-in-4bit \
  --prompt-style train \
  --candidate-set all \
  --attn-implementation eager
```

Normalized-reason adapter:

```bash
eval "$(python scripts/gpu_status.py --export)"
python scripts/score_action_modes.py \
  --model /data/LLM/Qwen3-8B \
  --adapter outputs/train_v0/qwen3_8b_action_lora_normreason_steps20/adapter \
  --dataset data/splits/reconcilebench_v0_dev.jsonl \
  --output outputs/scores/qwen3_8b_v0_dev_normreason_adapter_trainprompt_4bit.jsonl \
  --load-in-4bit \
  --prompt-style train \
  --candidate-set all \
  --attn-implementation eager
```

Combined report:

```bash
python scripts/compare_action_mode_runs.py \
  --dataset data/splits/reconcilebench_v0_dev.jsonl \
  --scores base=outputs/scores/qwen3_8b_v0_dev_base_trainprompt_4bit.jsonl \
  --scores normreason=outputs/scores/qwen3_8b_v0_dev_normreason_adapter_trainprompt_4bit.jsonl \
  --output-md reports/reconcile_v0_eval_base_vs_qlora.md \
  --output-csv reports/reconcile_v0_error_table.csv \
  --output-json reports/reconcile_v0_eval_base_vs_qlora.json
```

Terminal-action-only report:

```bash
python scripts/compare_action_mode_runs.py \
  --dataset data/splits/reconcilebench_v0_dev.jsonl \
  --scores base=outputs/scores/qwen3_8b_v0_dev_base_trainprompt_4bit.jsonl \
  --scores normreason=outputs/scores/qwen3_8b_v0_dev_normreason_adapter_trainprompt_4bit.jsonl \
  --exclude-continue-reasoning \
  --output-md reports/reconcile_v0_eval_terminal_only.md \
  --output-csv reports/reconcile_v0_error_table_terminal_only.csv
```

## Pairwise Judgment-Delta Data

Build train pairs only from the train split and forbid the dev split:

```bash
python scripts/build_pairwise_judgment_data.py \
  --dataset data/splits/reconcilebench_v0_train.jsonl \
  --forbid-source-dataset data/splits/reconcilebench_v0_dev.jsonl \
  --output data/pairwise/reconcilebench_v0_train_pairwise.jsonl \
  --manifest-output data/pairwise/reconcilebench_v0_train_pairwise_manifest.json \
  --split-name train \
  --max-pairs-per-example 2 \
  --seed 20260630
```

Build dev pairs separately for pairwise evaluation:

```bash
python scripts/build_pairwise_judgment_data.py \
  --dataset data/splits/reconcilebench_v0_dev.jsonl \
  --forbid-source-dataset data/splits/reconcilebench_v0_train.jsonl \
  --output data/pairwise/reconcilebench_v0_dev_pairwise.jsonl \
  --manifest-output data/pairwise/reconcilebench_v0_dev_pairwise_manifest.json \
  --split-name dev \
  --max-pairs-per-example 2 \
  --seed 20260630
```

Do not merge dev pairwise data into training. The builder checks source-id and
prompt-hash overlap against the forbidden split.

Pairwise base scoring:

```bash
eval "$(python scripts/gpu_status.py --export)"
python scripts/score_pairwise_judgments.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/pairwise/reconcilebench_v0_dev_pairwise.jsonl \
  --output outputs/pairwise_scores/qwen3_8b_v0_dev_pairwise_base_4bit.jsonl \
  --load-in-4bit \
  --attn-implementation eager

python scripts/evaluate_pairwise_scores.py \
  --dataset data/pairwise/reconcilebench_v0_dev_pairwise.jsonl \
  --scores base=outputs/pairwise_scores/qwen3_8b_v0_dev_pairwise_base_4bit.jsonl \
  --output-md reports/pairwise_v0_dev_base_eval.md \
  --output-json reports/pairwise_v0_dev_base_eval.json \
  --output-csv reports/pairwise_v0_dev_base_errors.csv
```

Next pairwise stage:

- Follow `docs/pairwise_v0_1_plan.md`.
- Do not run full pairwise QLoRA. First-stage pairwise training is rank-128
  LoRA only after v0.1 fork-state and scope-contract fields are inspectable.

Pairwise v0.1 base result:

- data: `data/pairwise/reconcilebench_v0_1_dev_pairwise.jsonl`;
- report: `reports/pairwise_v0_1_dev_base_eval.md`;
- Qwen3-8B 4-bit base winner accuracy: `0.7500`;
- fork-state accuracy: `0/3`;
- scope-contract accuracy: `11/13`;
- peak allocated CUDA memory: about `7217 MB`.

## Pairwise Rank-128 LoRA

Training policy:

- Do not use QLoRA for first-stage pairwise runs.
- Do not use full-parameter fine-tuning.
- Use rank-128 LoRA and tune memory with `--batch-size`,
  `--gradient-accumulation-steps`, and `--max-length`.
- Prefer `data/pairwise/reconcilebench_v0_1_train_pairwise_posbalanced.jsonl`
  for new runs, and evaluate side bias on
  `data/pairwise/reconcilebench_v0_1_dev_pairwise_posbalanced.jsonl`.
- Reject runs with `position_bias_gate = fail`; the current gate fails if the
  predicted majority side is above `0.80`, the predicted A-rate differs from
  gold A-rate by more than `0.20`, min A/B recall is below `0.50`, or swap
  consistency is below `0.70`.
- Use `winner_only` scoring for continuity with earlier pairwise reports. Use
  `--score-mode compact_structured_judgment` only as an auxiliary
  target-alignment diagnostic because it scores gold metadata fields from the
  pair record.
- Do not compare compactscore winner accuracy directly against earlier
  winner-only reports as the main method result. Report compactscore only as
  target-alignment evidence beside the winner-only gate.

Current preferred position-balanced compact target example:

```bash
python scripts/train_pairwise_lora.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/pairwise/reconcilebench_v0_1_train_pairwise_posbalanced.jsonl \
  --output-dir outputs/train_pairwise_lora/qwen3_8b_v0_1_r128_posbalanced_compact_lr3e6_s24_len1024 \
  --target-style compact_structured_judgment \
  --max-length 1024 \
  --max-steps 24 \
  --batch-size 1 \
  --gradient-accumulation-steps 16 \
  --lr 3e-6 \
  --lora-r 128 \
  --lora-alpha 256 \
  --attn-implementation eager
```

Official first-stage pairwise runs must omit `--load-in-4bit`.

Reduced target next ablation:

- Use `--target-style compact_winner_delta_tag` to train/generate only:

```text
WINNER: A|B
DELTA_TAG: <current discrete delta tag>
```

- Keep `winner_only` constrained scoring as the primary gate.
- Treat reduced generation as a behavior/format check, not as proof of final
  assistant safety behavior.
- If `DELTA_TAG` remains label-confused, move it to a constrained scorer
  rather than adding more metadata fields back into generation.

```bash
eval "$(python scripts/gpu_status.py --export)"
python scripts/train_pairwise_lora.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/pairwise/reconcilebench_v0_1_train_pairwise_posbalanced.jsonl \
  --output-dir outputs/train_pairwise_lora/qwen3_8b_v0_1_r128_posbalanced_winner_delta_lr3e6_s24_len1024 \
  --target-style compact_winner_delta_tag \
  --max-length 1024 \
  --max-steps 24 \
  --batch-size 1 \
  --gradient-accumulation-steps 16 \
  --lr 3e-6 \
  --lora-r 128 \
  --lora-alpha 256 \
  --attn-implementation eager

python scripts/score_pairwise_judgments.py \
  --model /data/LLM/Qwen3-8B \
  --adapter outputs/train_pairwise_lora/qwen3_8b_v0_1_r128_posbalanced_winner_delta_lr3e6_s24_len1024/adapter \
  --dataset data/pairwise/reconcilebench_v0_1_dev_pairwise_posbalanced.jsonl \
  --output outputs/pairwise_scores/qwen3_8b_v0_1_dev_posbalanced_r128_winner_delta_winneronly.jsonl \
  --score-mode winner_only \
  --attn-implementation eager

python scripts/generate_pairwise_compact_judgments.py \
  --model /data/LLM/Qwen3-8B \
  --adapter outputs/train_pairwise_lora/qwen3_8b_v0_1_r128_posbalanced_winner_delta_lr3e6_s24_len1024/adapter \
  --dataset data/pairwise/reconcilebench_v0_1_dev_pairwise_posbalanced.jsonl \
  --output outputs/pairwise_generations/qwen3_8b_v0_1_dev_posbalanced_r128_winner_delta_gen.jsonl \
  --target-style compact_winner_delta_tag \
  --max-new-tokens 48 \
  --attn-implementation eager
```

Current reduced-target result:

- `reports/pairwise_v0_1_winner_delta_summary.md`;
- output dir:
  `outputs/train_pairwise_lora/qwen3_8b_v0_1_r128_posbalanced_winner_delta_lr3e6_s24_len1024_b2`;
- batch size `2`, grad accumulation `8`, effective batch `16`;
- no QLoRA and no full-parameter fine-tuning;
- peak training allocation: `35752.42 MB`; total observed GPU1 usage during
  training was about `67GB`, below the preferred `70GB+` utilization target;
- winner-only scoring: original dev ties full base at `22/28`; position-balanced
  dev is `43/56`, swap `19/28`, gate fail;
- reduced generation: adapter beats reduced-prompt base (`23/28` vs `22/28`
  original; `45/56` vs `41/56` position-balanced), but swap remains
  `19/28` and exact `DELTA_TAG` accuracy is `0`;
- constrained `DELTA_TAG` scoring also fails to recover the current discrete
  labels: adapter gets `6/28` original and `10/56` position-balanced;
- next step: keep `WINNER` generation as behavior signal and rebuild rationale
  labels before generating or scoring them again.

Observable target next ablation:

- Use `--target-style compact_winner_obs_tag` to train/generate only:

```text
WINNER: A|B
OBS_TAG: <observable winner-action tag>
```

- `OBS_TAG` labels:
  `ask_clarification`, `direct_answer`, `partial_allowed`,
  `preserve_fork_state`, `refuse`, `safe_high_level`, `safe_redirect`.
- The tag is derived from the winner card's visible action mode; fork-state or
  `lost_fork_state` records use `preserve_fork_state`.
- This target is intentionally close to `GOLD_ACTION`, so do not treat label
  accuracy as the main method result. Primary gates remain winner accuracy,
  A/B side balance, and parent-level swap consistency on position-balanced dev.
- Official training runs must stay rank-128 LoRA, omit `--load-in-4bit`, and
  avoid full-parameter fine-tuning.

Eval-only generation before training:

```bash
python scripts/generate_pairwise_compact_judgments.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/pairwise/reconcilebench_v0_1_dev_pairwise_posbalanced.jsonl \
  --output outputs/pairwise_generations/qwen3_8b_v0_1_dev_posbalanced_fullbase_obs_tag_gen.jsonl \
  --target-style compact_winner_obs_tag \
  --max-new-tokens 48 \
  --attn-implementation eager

python scripts/generate_pairwise_compact_judgments.py \
  --model /data/LLM/Qwen3-8B \
  --adapter outputs/train_pairwise_lora/qwen3_8b_v0_1_r128_posbalanced_winner_delta_lr3e6_s24_len1024_b2/adapter \
  --dataset data/pairwise/reconcilebench_v0_1_dev_pairwise_posbalanced.jsonl \
  --output outputs/pairwise_generations/qwen3_8b_v0_1_dev_posbalanced_r128_winner_delta_obs_tag_gen.jsonl \
  --target-style compact_winner_obs_tag \
  --max-new-tokens 48 \
  --attn-implementation eager

python scripts/evaluate_pairwise_scores.py \
  --dataset data/pairwise/reconcilebench_v0_1_dev_pairwise_posbalanced.jsonl \
  --scores fullbase_obs=outputs/pairwise_generations/qwen3_8b_v0_1_dev_posbalanced_fullbase_obs_tag_gen.jsonl \
  --scores r128_winner_delta_obs=outputs/pairwise_generations/qwen3_8b_v0_1_dev_posbalanced_r128_winner_delta_obs_tag_gen.jsonl \
  --output-md reports/pairwise_v0_1_dev_posbalanced_obs_tag_generation.md \
  --output-json reports/pairwise_v0_1_dev_posbalanced_obs_tag_generation.json \
  --output-csv reports/pairwise_v0_1_dev_posbalanced_obs_tag_generation_errors.csv
```

Completed rank-128 LoRA run:

```bash
eval "$(python scripts/gpu_status.py --export)"
python scripts/train_pairwise_lora.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/pairwise/reconcilebench_v0_1_train_pairwise_posbalanced.jsonl \
  --output-dir outputs/train_pairwise_lora/qwen3_8b_v0_1_r128_posbalanced_obs_tag_lr3e6_s24_len1024_b2 \
  --target-style compact_winner_obs_tag \
  --max-length 1024 \
  --max-steps 24 \
  --batch-size 2 \
  --gradient-accumulation-steps 8 \
  --lr 3e-6 \
  --lora-r 128 \
  --lora-alpha 256 \
  --attn-implementation eager
```

Current training result:

- output dir:
  `outputs/train_pairwise_lora/qwen3_8b_v0_1_r128_posbalanced_obs_tag_lr3e6_s24_len1024_b2`;
- batch size `3` OOMed under shared GPU load;
- batch size `2`, grad accumulation `8`, max length `1024`, 24 steps, lr
  `3e-6`, rank/alpha `128/256` completed;
- no QLoRA and no full-parameter fine-tuning;
- loss `6.4620 -> 0.7934`;
- process peak allocated CUDA memory `35413.57 MB`;
- observed total GPU1 memory reached `78328 MB`.

Current observable-tag eval-only result:

- summary: `reports/pairwise_v0_1_obs_tag_generation_summary.md`;
- no new training was used; this evaluates the existing rank-128 winner-delta
  adapter under the `compact_winner_obs_tag` generation target;
- original dev: full base `22/28`, existing adapter `23/28`;
- position-balanced dev: full base `42/56`, swap `16/28`, gate fail; existing
  adapter `44/56`, swap `20/28`, gate pass;
- position-balanced fork-state improves from `4/6` to `5/6`;
- exact `OBS_TAG` accuracy is still weak (`8/56` for the adapter on
  position-balanced dev), so use it only as an auxiliary support field.

Current observable-tag adapter and fresh-heldout result:

- summary: `reports/pairwise_v0_1_obs_tag_adapter_and_heldout_summary.md`;
- heldout source: `data/heldout/reconcilebench_v0_fork_scope_holdout.jsonl`;
- heldout pairwise:
  `data/pairwise/reconcilebench_v0_1_fork_scope_holdout_pairwise.jsonl`;
- heldout position-balanced pairwise:
  `data/pairwise/reconcilebench_v0_1_fork_scope_holdout_pairwise_posbalanced.jsonl`;
- source set: 16 Chinese fork/scope examples;
- position-balanced audit: `96/96` clean, with no forbidden source-id or
  prompt-hash overlap against existing v0.1 train/dev;
- position-balanced heldout:
  - fullbase `61/96`, swap `27/48`, gate fail;
  - existing winner-delta adapter `68/96`, swap `32/48`, gate fail;
  - new obs-tag adapter `68/96`, swap `32/48`, gate fail;
- exact `OBS_TAG` improves for the new obs-tag adapter (`38/96` vs `20/96`
  for the existing adapter), but this is not the primary gate.

Important render caveat:

- Fresh heldout pairwise files were regenerated after fixing `render_card`
  newlines.
- Historical train/dev pairwise JSONL files were not regenerated and still
  reflect the earlier concatenated-field rendering.
- Do not retroactively describe historical adapters as trained on the fixed
  rendering.

Heldout eval command shape:

```bash
python scripts/generate_pairwise_compact_judgments.py \
  --model /data/LLM/Qwen3-8B \
  --adapter outputs/train_pairwise_lora/qwen3_8b_v0_1_r128_posbalanced_obs_tag_lr3e6_s24_len1024_b2/adapter \
  --dataset data/pairwise/reconcilebench_v0_1_fork_scope_holdout_pairwise_posbalanced.jsonl \
  --output outputs/pairwise_generations/qwen3_8b_v0_1_heldout_fork_scope_posbalanced_r128_obs_tag_gen.jsonl \
  --target-style compact_winner_obs_tag \
  --max-new-tokens 48 \
  --attn-implementation eager

python scripts/evaluate_pairwise_scores.py \
  --dataset data/pairwise/reconcilebench_v0_1_fork_scope_holdout_pairwise_posbalanced.jsonl \
  --scores r128_obs_tag=outputs/pairwise_generations/qwen3_8b_v0_1_heldout_fork_scope_posbalanced_r128_obs_tag_gen.jsonl \
  --output-md reports/pairwise_v0_1_heldout_fork_scope_posbalanced_obs_tag_generation.md \
  --output-json reports/pairwise_v0_1_heldout_fork_scope_posbalanced_obs_tag_generation.json \
  --output-csv reports/pairwise_v0_1_heldout_fork_scope_posbalanced_obs_tag_generation_errors.csv
```

Current smoke report:

- `reports/pairwise_v0_1_dev_lora_r128_smoke.md`;
- structured target improves fork-state from `1/3` to `2/3` but drops overall
  winner accuracy from `0.7857` to `0.6429`;
- winner-only target collapses toward one candidate side and is not useful as
  the next direction.

Current position-balanced compact reports:

- `reports/pairwise_v0_1_r128_posbalanced_compact_summary.md`;
- `reports/pairwise_v0_1_compactscore_alignment_summary.md`;
- `reports/pairwise_v0_1_compact_generation_summary.md`;
- `reports/pairwise_v0_1_compact_generation_mismatch_analysis.md`;
- `reports/pairwise_v0_1_compact_ontology_generation_summary.md`;
- winner-only scoring: adapters improve fork-state and avoid simple side
  collapse, but still fail the position-balanced swap-consistency gate;
- compact structured scoring: adapters reach 100% label-conditioned
  target-aligned dev scores, which confirms target learning but remains an
  optimistic diagnostic;
- greedy compact generation: adapters do not beat the full BF16 base, so the
  current rank-128 compact LoRA result is not a positive method result;
- mismatch analysis: strict full-target match is too harsh as a standalone
  behavioral metric, but it reveals the current compact target/prompt causes
  field omission and schema confusion;
- ontology prompt: explicit labels reduce schema-confusion labels, but winner
  selection and swap consistency regress. Do not use ontology prompt as the
  default compact generation prompt; decompose the one-shot compact target
  before more training steps.

Compact generation check:

```bash
python scripts/generate_pairwise_compact_judgments.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/pairwise/reconcilebench_v0_1_dev_pairwise_posbalanced.jsonl \
  --adapter outputs/train_pairwise_lora/qwen3_8b_v0_1_r128_posbalanced_compact_lr3e6_s24_len1024/adapter \
  --output outputs/pairwise_generations/qwen3_8b_v0_1_dev_posbalanced_r128_posbalanced_compact_lr3e6_s24_len1024_compact_gen.jsonl \
  --max-new-tokens 96 \
  --attn-implementation eager

python scripts/evaluate_pairwise_scores.py \
  --dataset data/pairwise/reconcilebench_v0_1_dev_pairwise_posbalanced.jsonl \
  --scores r128_lr3e6_len1024_gen=outputs/pairwise_generations/qwen3_8b_v0_1_dev_posbalanced_r128_posbalanced_compact_lr3e6_s24_len1024_compact_gen.jsonl \
  --output-md reports/pairwise_v0_1_dev_posbalanced_compact_generation_compare.md \
  --output-json reports/pairwise_v0_1_dev_posbalanced_compact_generation_compare.json \
  --output-csv reports/pairwise_v0_1_dev_posbalanced_compact_generation_compare_errors.csv
```

Official first-stage compact generation checks must omit `--load-in-4bit`.

Ontology prompt diagnostic:

```bash
python scripts/generate_pairwise_compact_judgments.py \
  --model /data/LLM/Qwen3-8B \
  --dataset data/pairwise/reconcilebench_v0_1_dev_pairwise_posbalanced.jsonl \
  --adapter outputs/train_pairwise_lora/qwen3_8b_v0_1_r128_posbalanced_compact_lr1e5_s24/adapter \
  --output outputs/pairwise_generations/qwen3_8b_v0_1_dev_posbalanced_r128_posbalanced_compact_lr1e5_s24_ontology_gen.jsonl \
  --prompt-style ontology \
  --max-new-tokens 128 \
  --attn-implementation eager
```

Treat this as an eval-only diagnostic. It keeps the target unchanged and should
not be connected to `scripts/train_pairwise_lora.py` as a training prompt.

Compact generation mismatch analysis:

```bash
python scripts/analyze_compact_generation_mismatches.py \
  --generation full_base_pos=outputs/pairwise_generations/qwen3_8b_v0_1_dev_posbalanced_fullbase_compact_gen.jsonl \
  --generation r128_lr1e5_pos=outputs/pairwise_generations/qwen3_8b_v0_1_dev_posbalanced_r128_posbalanced_compact_lr1e5_s24_compact_gen.jsonl \
  --generation r128_lr3e6_len1024_pos=outputs/pairwise_generations/qwen3_8b_v0_1_dev_posbalanced_r128_posbalanced_compact_lr3e6_s24_len1024_compact_gen.jsonl \
  --output-md reports/pairwise_v0_1_compact_generation_mismatch_analysis.md \
  --output-json reports/pairwise_v0_1_compact_generation_mismatch_analysis.json \
  --output-csv reports/pairwise_v0_1_compact_generation_mismatch_samples.csv
```
