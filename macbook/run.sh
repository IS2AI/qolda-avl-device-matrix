#!/usr/bin/env bash
# Device 2 (Apple M4 Pro / Metal) — run the benchmark matrix.
#
# bench.py PARSES power.log; it does not start the sampler. Without a running
# powermetrics it aborts with "FATAL: no power samples". This script starts the
# sampler, runs the matrix, and stops the sampler on exit.
#
# Requires sudo for powermetrics. The original runs used a passwordless sudoers
# rule so the sampler could run unattended; that rule was removed afterwards.
# Either authenticate interactively when prompted, or re-add the rule and
# REMOVE IT when you are done:
#   sudo rm /etc/sudoers.d/qolda-powermetrics
set -euo pipefail
cd "$(dirname "$0")"

BIN=llama.cpp/build/bin/llama-server
for f in "$BIN" prompts_text.txt bench_image.jpg bench_audio_10s.wav \
         bench_audio_30s.wav models; do
  [ -e "$f" ] || { echo "FATAL: missing $f — run ./setup.sh first"; exit 1; }
done
mkdir -p logs

# One persistent sampler spanning the whole matrix, 200 ms interval.
sudo powermetrics --samplers cpu_power,gpu_power -i 200 > power.log &
PM=$!
# caffeinate: system default displaysleep is 2 min and a slept display changes
# the SoC power floor mid-matrix.
caffeinate -dims &
CAF=$!
cleanup() { sudo kill "$PM" 2>/dev/null || true; kill "$CAF" 2>/dev/null || true; }
trap cleanup EXIT

sleep 5   # let the sampler produce a first block before the idle baseline

# No arguments: all five variants, then both control cells.
# A variant name limits the run, e.g.  ./run.sh Q4_K_M
python3 bench.py "$@"

python3 aggregate.py results.csv
echo "OK -> results.csv, raw_runs.jsonl, idle_baselines.json"
