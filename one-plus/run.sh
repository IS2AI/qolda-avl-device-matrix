#!/usr/bin/env bash
# Device 3 (OnePlus 13R) — run the benchmark matrix from the Mac over wireless ADB.
#
# The phone must be UNPLUGGED: power comes from BatteryManager (mA x mV), which
# reads zero or garbage while charging. Screen off, airplane mode on with WiFi
# re-enabled, so the only radio traffic is the ADB link.
#
# Wireless, not `adb forward`. adb forward tunnels TCP through adb's own
# multiplexing and distorts TTFT; the measured path is a direct TCP connection.
set -euo pipefail
cd "$(dirname "$0")"

: "${ADB_SERIAL:?set ADB_SERIAL, e.g. export ADB_SERIAL=<phone-ip>:5555}"
DEV_ROOT=/data/local/tmp/qolda

for f in prompts_text.txt bench_image.jpg bench_audio_10s.wav bench_audio_30s.wav; do
  [ -e "$f" ] || { echo "FATAL: missing $f — run ./setup.sh first"; exit 1; }
done
adb -s "$ADB_SERIAL" get-state >/dev/null 2>&1 \
  || { echo "FATAL: $ADB_SERIAL not reachable. adb tcpip 5555 && adb connect <ip>:5555"; exit 1; }
adb -s "$ADB_SERIAL" shell "[ -x $DEV_ROOT/bin/llama-server ]" \
  || { echo "FATAL: llama-server not staged on device — run ./setup.sh"; exit 1; }

PLUGGED=$(adb -s "$ADB_SERIAL" shell dumpsys battery | awk -F': ' '/AC powered|USB powered/{print $2}' | tr -d '\r' | sort -u)
case "$PLUGGED" in *true*) echo "FATAL: phone is charging. Unplug it: battery draw is the power boundary."; exit 1;; esac

adb -s "$ADB_SERIAL" shell input keyevent 26 || true   # screen off

# 1. Calibrate the power sampler against the battery register.
python3 calibrate_power.py --seconds 90

# 2. Derive image/audio token counts from the server's own prompt_n.
python3 token_census.py

# 3. The matrix, in the order it was originally run. Resumable: completed cells
#    are read back from raw_runs.jsonl, so a re-run picks up where it stopped.
python3 bench.py --thermal sustained --variants Q4_K_M
python3 bench.py --thermal cold
python3 bench.py --thermal sustained --variants Q5_K_M,Q6_K,Q8_0 --controls
python3 bench.py --thermal sustained --variants BF16

# NOTE: `python3 bench.py --decay` (the 20-minute thermal decay curve) is part of
# the protocol but was NEVER RUN. There is no thermal_decay.csv in this repo.

python3 aggregate.py results.csv
echo "OK -> results.csv, raw_runs.jsonl"
