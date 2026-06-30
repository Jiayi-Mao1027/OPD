#!/usr/bin/env bash
set -euo pipefail

MODEL="${MODEL:-/data/LLM/Qwen3-8B}"
TRAIN_DATASET="${TRAIN_DATASET:-data/splits/reconcilebench_v0_train.jsonl}"
EVAL_DATASET="${EVAL_DATASET:-data/splits/reconcilebench_v0_dev.jsonl}"
TARGET_STYLE="${TARGET_STYLE:-normalized_reason}"
MAX_STEPS="${MAX_STEPS:-20}"
MAX_LENGTH="${MAX_LENGTH:-768}"
EVAL_MAX_NEW_TOKENS="${EVAL_MAX_NEW_TOKENS:-96}"
ATTN_IMPLEMENTATION="${ATTN_IMPLEMENTATION:-eager}"
MIN_FREE_MB="${MIN_FREE_MB:-20000}"
MAX_USED_MB="${MAX_USED_MB:-70000}"
OUTPUT_DIR="${OUTPUT_DIR:-outputs/train_v0/qwen3_8b_action_lora_${TARGET_STYLE}_steps${MAX_STEPS}}"

cd "$(dirname "$0")/.."

source /data/conda/etc/profile.d/conda.sh
conda activate mjy

export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.2}"
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
export PYTHONPATH="$PWD/src"

echo "== Git =="
git status --short --branch
git rev-parse --short HEAD

echo "== Tests =="
pytest -q

echo "== GPU selection =="
python scripts/gpu_status.py --min-free-mb "$MIN_FREE_MB" --max-used-mb "$MAX_USED_MB"
eval "$(python scripts/gpu_status.py --min-free-mb "$MIN_FREE_MB" --max-used-mb "$MAX_USED_MB" --export)"
echo "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES"

echo "== Train/eval =="
python scripts/train_action_mode_lora.py \
  --model "$MODEL" \
  --dataset "$TRAIN_DATASET" \
  --eval-dataset "$EVAL_DATASET" \
  --output-dir "$OUTPUT_DIR" \
  --max-steps "$MAX_STEPS" \
  --max-length "$MAX_LENGTH" \
  --eval-max-new-tokens "$EVAL_MAX_NEW_TOKENS" \
  --attn-implementation "$ATTN_IMPLEMENTATION" \
  --target-style "$TARGET_STYLE"

echo "== Metrics =="
cat "$OUTPUT_DIR/metrics.json"
cat "$OUTPUT_DIR/eval_metrics.json"
