#!/usr/bin/env bash
# Device 2 (Apple M4 Pro / Metal) — build llama.cpp and fetch the model files.
# Transcribed from summary.md "Exact commands run". Run once, from this directory.
set -euo pipefail
cd "$(dirname "$0")"

COMMIT=ea63b4d32ea1b66bdbe369be7f9443f6c00f8b31
PATCH="$(cd ../protocol && pwd)/qwen3avl-support.patch"

command -v cmake >/dev/null || { echo "FATAL: cmake not found"; exit 1; }
command -v hf    >/dev/null || { echo "FATAL: huggingface-cli (hf) not found"; exit 1; }

# The drivers read the fixed inputs from their own directory. The repo keeps one
# canonical copy in protocol/; materialise it here.
cp ../protocol/prompts_text.txt ../protocol/bench_image.jpg \
   ../protocol/bench_audio_10s.wav ../protocol/bench_audio_30s.wav .

if [ ! -d llama.cpp ]; then
  git clone https://github.com/ggml-org/llama.cpp llama.cpp
fi
(
  cd llama.cpp
  git checkout "$COMMIT"
  # Patch must apply with zero fuzz. A stock build silently loses audio support
  # and the resulting rows look like model failures rather than a build error.
  git apply --check -v "$PATCH"
  git apply -v "$PATCH"
  cmake -B build -DCMAKE_BUILD_TYPE=Release
  cmake --build build -j --target llama-server llama-mtmd-cli llama-tokenize
)

# 5 quant variants + 2 mmproj files, ~19 GiB total.
hf download issai/Qolda-AVL-5B-GGUF --local-dir models --exclude "imatrix/*"

mkdir -p logs
echo "OK. Verify artifact hashes against file_manifest.json before benchmarking."
