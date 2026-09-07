# Qolda-AVL-5B deployment benchmark — Device 3: OnePlus 13R (Android)

Measured results table: `results.csv`. Raw per-run records (full thermal zone sets,
per-sample power, server timings objects): `raw_runs.jsonl`. Thermal decay curve:
`thermal_decay.csv`. Power calibration and environment: `env.json`.

**These are speed measurements, not quality measurements.** No output quality was
evaluated; the model card already provides perplexity, KLD and top-1 agreement per
quant. Every measured run uses `ignore_eos = true` with a fixed `n_predict = 256`,
so every run emits exactly 256 tokens regardless of content and the throughput
window is identical by construction.

---

## Environment

| | |
|---|---|
| Device | OnePlus 13R, model `CPH2691` (`OP5D3BL1`) |
| Device class | `flagship-smartphone` |
| SoC | Qualcomm Snapdragon 8 Gen 3, `SM8650` (platform `pineapple`) |
| CPU | 8 cores, ARM part `0xd80` (Cortex-X4 prime); max freqs 3.3024 / 3.1488 / 2.9568 / 2.2656 GHz |
| RAM | 15,569,104 kB total (14.85 GiB, "16 GB" nominal) |
| Swap | 9,961,468 kB zram (9.50 GiB) |
| Android | 16 (SDK 36), security patch 2026-07-01 |
| OxygenOS | V16.1.0, build `CPH2691_16.0.9.402(EX01)` |
| Backend | `CPU (ARM NEON/i8mm)` — CPU only, no OpenCL/Adreno backend attempted |
| NDK | r29 (`29.0.14206865`) |
| Clang | Android clang 21.0.0 (`13989888`, based on `r563880c`), target `aarch64-linux-android` |
| cmake / ninja | 4.1.0 / 1.13.2 |
| Host | macOS, Apple silicon (cross-compile only; no measurement on host) |
| Battery level range | *(filled at end of session)* |
| Ambient room temperature | ~23 °C (operator-reported) |
| Case state | **Bare** — no case, no fan, no cooling pad, device stationary |

Device configuration during all measured runs: **unplugged** (`USB powered: false`,
`AC powered: false`, `status: 3` discharging), **screen off** (`mWakefulness=Dozing`),
**airplane mode on** with cellular confirmed `POWER_OFF` (`mVoiceRegState=3`,
`mDataRegState=3`) and Bluetooth off. WiFi is deliberately left up as the ADB and
measurement transport (D2). Android deep-idle is disabled (`cmd deviceidle disable`)
and a host-side ICMP keepalive holds the WiFi radio in active mode (D13); both are
present during the idle-power baseline as well as the measured runs, so their power
cost cancels in `avg_power_w − idle_power_w`. Nothing is installed on the device and
no shell is held open; `llama-server` is launched detached under `nohup` and every
sample is a discrete `adb shell` invocation.

## llama.cpp build

- Commit **`ea63b4d32ea1b66bdbe369be7f9443f6c00f8b31`** (`ea63b4d`), identical to the
  other devices. On-device `--version` reports `version: 10198 (ea63b4d32)`.
- Patch **`qwen3avl-support.patch`** applied cleanly — `git apply --check` passed with
  no fuzz. sha256 `bb27de1efd5b546d74b834395570f49d5e017db872f0586a771edf59d0f89bf3`.
  8 files changed, 228 insertions(+), 8 deletions(-): `conversion/__init__.py`,
  `conversion/qwen3avl.py` (new), `gguf-py/gguf/constants.py`, `tools/mtmd/clip-graph.h`,
  `tools/mtmd/clip-impl.h`, `tools/mtmd/clip.cpp`,
  `tools/mtmd/models/whisper-enc.cpp`, `tools/mtmd/mtmd.cpp`.
- `patch_applied = yes` on every row. No stock-llama.cpp fallback was used at any point.

Configure:

```
cmake -B build-android -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE=$NDK/build/cmake/android.toolchain.cmake \
  -DANDROID_ABI=arm64-v8a \
  -DANDROID_PLATFORM=android-28 \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_NATIVE=OFF \
  -DGGML_CPU_ARM_ARCH=armv8.2-a+dotprod+i8mm \
  -DGGML_OPENMP=OFF \
  -DLLAMA_CURL=OFF \
  -DLLAMA_BUILD_TESTS=OFF \
  -DLLAMA_BUILD_EXAMPLES=OFF
cmake --build build-android -j 10 \
  --target llama-server llama-mtmd-cli llama-tokenize
```

**Exact arch flags: `-march=armv8.2-a+dotprod+i8mm`.** CMake feature probes:

| Probe | Result |
|---|---|
| `HAVE_DOTPROD` | **Success** — dotprod enabled |
| `HAVE_MATMUL_INT8` | **Success** — i8mm enabled |
| `HAVE_FMA` | Success |
| `HAVE_SVE` | Failed (not requested in `-march`) |
| `HAVE_SME` | Failed |
| `HAVE_FP16_VECTOR_ARITHMETIC` | **Failed** |

`GGML_USE_CPU_REPACK` and `GGML_USE_LLAMAFILE` are enabled. Binaries verified as
`ELF 64-bit LSB, ARM aarch64` and execute natively on the device.

Note on `HAVE_FP16_VECTOR_ARITHMETIC`: `armv8.2-a+dotprod+i8mm` does not set
`__ARM_FEATURE_FP16_VECTOR_ARITHMETIC`, so ggml's fp16 vector paths are compiled
out even though Cortex-X4/A720 support them. Adding `+fp16` would likely speed the
F16 Whisper encoder, which is the dominant cost in every audio and vision row. The
protocol froze the flags at i8mm + dotprod, so this was **not** changed; it is
recorded here as a known headroom item rather than acted on.

## Artifacts

Fixed artifacts — **all four sha256 match the protocol exactly**, verified on the
host and again on-device after transfer (byte-identical post-push):

| File | sha256 | Status |
|---|---|---|
| `bench_image.jpg` | `d45840444cdef3c8d81eaa73c720f78e49fd3274c510fc49fc12665c43bb2330` | match |
| `prompts_text.txt` | `bb5c5cf054819d5775533e5fb8d2914196865351b1c5144fe7bdee35759dcc09` | match |
| `bench_audio_30s.wav` | `94c91da6916aa32b9ba6cd5e602a7eb941c3b2b637f46a1744dff7a8602bbbc7` | match |
| `bench_audio_10s.wav` | `c00cefb4f2d1c942f02eedebbc21dee4ccbc90cd1b2e08a40f18f162cfa77d0c` | match |

Nothing was regenerated or substituted.

Model files (from `issai/Qolda-AVL-5B-GGUF`). Sizes are GiB (the protocol table
quotes GB; the two agree):

| File | GiB | bytes | sha256[:12] |
|---|---|---|---|
| `BF16/Qolda-AVL-5B-BF16.gguf` | 7.50 | 8,051,286,368 | `7df60f9052bd` |
| `Q8_0/Qolda-AVL-5B-Q8_0.gguf` | 3.99 | 4,280,406,368 | `613406fad8ab` |
| `Q6_K/Qolda-AVL-5B-Q6_K.gguf` | 3.08 | 3,306,262,368 | `d392af001fee` |
| `Q5_K_M/Qolda-AVL-5B-Q5_K_M.gguf` | 2.69 | 2,889,515,104 | `193793b63208` |
| `Q4_K_M/Qolda-AVL-5B-Q4_K_M.gguf` | 2.33 | 2,497,282,144 | `4846476c27ae` |
| `mmproj/mmproj-Qolda-AVL-5B-F16.gguf` | 2.04 | 2,193,746,656 | `041aa58d1d39` |
| `mmproj/mmproj-Qolda-AVL-5B-vision-only-F16.gguf` | 0.78 | 836,180,480 | `c06b37209e45` |

## Prompt parsing

`prompts_text.txt` was split on opening markers only (`<<<PROMPT_128>>>`,
`<<<PROMPT_512>>>`, `<<<PROMPT_2048>>>`); each body runs from the line after its
marker to the next marker or EOF, marker lines stripped, trailing whitespace
stripped. **Exactly 3 non-empty prompts recovered** (189 / 797 / 3211 characters).

## Token counts

Counted once. `llama-tokenize --no-bos` was run **on-device with the patched
`ea63b4d` build**, and cross-checked against the server-reported `prompt_n`.

| Item | llama-tokenize | server `prompt_n` | Protocol reference | Verdict |
|---|---|---|---|---|
| text-128 | 128 | 128 | 128 | **match** |
| text-512 | 513 | 513 | 513 | **match** |
| text-2048 | 2048 | 2048 | 2048 | **match** |
| vision instruction | 65 | — | 65 | **match** |
| audio instruction | 28 | — | 28 | **match** |

**Tokenizer cross-check: no divergence.** The prompt file was generated with a
Homebrew llama.cpp build, but re-tokenised under patched `ea63b4d` it yields
identical counts for all three text prompts. No label adjustment is needed, and
`text-512` genuinely tokenises to **513** as the protocol states.

Modality token counts, derived from server `prompt_n` minus the instruction minus
12 tokens of chat-template overhead (the overhead is pinned by the vision row:
1101 − 1024 − 65 = 12):

| Mode | server `prompt_n` | derived | Expected |
|---|---|---|---|
| vision | 1101 | **1024 image tokens** | 1024 min for Qwen-VL |
| audio-30s | 1540 | **1500 audio tokens** | ~1500 (~50 tok/s × 30 s) |
| audio-10s | 540 | **500 audio tokens** | ~500 (~50 tok/s × 10 s) |

All three land exactly on the protocol's expected figures.

## Thermal zone mapping

104 zones exist under `/sys/class/thermal/`; all are readable by the shell user.
Zones sampled during runs (type → role):

| Zone type | Role |
|---|---|
| `cpu-0-0-0`, `cpu-0-1-0` | CPU cluster 0 |
| `cpu-1-0-0` … `cpu-1-2-2` | CPU cluster 1 |
| `cpu-2-0-0` … `cpu-2-2-1` | CPU cluster 2 |
| `cpuss-0` … `cpuss-3` | CPU subsystem aggregate |
| `gpuss-0` … `gpuss-7` | GPU subsystem (idle here — CPU backend) |
| `ddr` | DRAM |
| `shell_front`, `shell_frame`, `shell_back` | **Skin temperature** (chassis) |
| `skin-msm-therm` | SoC-side skin sensor |
| `xo-therm` | Crystal oscillator / board reference |
| `vbat` | Reports battery **millivolts**, not temperature — excluded |

`cpu-1-2-0` is used as the representative **SoC/big-core** temperature and
`shell_back` as the representative **skin** temperature in the `notes` column.
The full zone set for every run is in `raw_runs.jsonl`.

Reference points measured this session: idle-at-rest `cpu-1-2-0` ≈ 33–35 °C,
`shell_back` ≈ 30 °C; under sustained CPU load `cpu-1-2-0` reached 66.1 °C with
`shell_back` at 41.2 °C and battery at 38.1 °C.

## Power methodology

**The protocol's specified source does not exist on this device.** Every node in
`/sys/class/power_supply/battery/` — including `current_now`, `voltage_now` and
`uevent` — returns `Permission denied` to the shell user on this build
(Android 16 / OxygenOS 16 SELinux). `dumpsys powerstats` lists **no
EnergyConsumers**, so there are no ODPM rails either. This is deviation D1.

Substitute source: `cmd battery get -f current_now` (BatteryManager) for current
and `dumpsys battery` → `voltage` for voltage. The OEM `dumpsys battery` →
`Battery current` field returned **byte-identical values** across 90 samples, so
the two candidates are the same register surfaced twice, not independent sources.

**Unit scaling determined by the protocol's own sanity check**, on a 90-sample
unplugged screen-off idle baseline:

| Interpretation | Idle power | Verdict |
|---|---|---|
| µA × µV (protocol assumption) | 0.000000 W | absurd — six orders of magnitude low |
| **mA × mV** | **0.406 W** | inside the 0.3–0.8 W band |

This OEM reports **mA and mV**. Boundary is `battery draw (whole device)`; the
idle baseline is subtracted.

Idle baseline, 120 s unplugged / screen off / airplane mode, n = 88 at 1 Hz:
mean current 99.1 mA, median 115.5 mA, σ 61.8 mA, voltage 4.3696 V, **19 of 88
samples read exactly 0 mA** (SoC entering deep idle between ADB wakeups — real
behaviour, not a failed read; under load the signal is stable, so this affects
only the baseline).

- **`idle_power_w` = 0.433 W** — mean over all samples including zeros, matching
  the protocol's "mean power over that window" rule. This is the value in `results.csv`.
- Alternative excluding zeros: **0.552 W**. Because `energy_j_per_1k_tok =
  (avg_power_w − idle_power_w) × decode_seconds / generated_tokens × 1000`, using
  the higher baseline reduces every energy figure by
  `0.119 × decode_seconds / generated_tokens × 1000` J/1k-tok — about 11.9 J/1k-tok
  per second-per-token, i.e. roughly 11.1 J/1k-tok at a decode rate of 10.7 tok/s.
  A reviewer can recompute either way from `raw_runs.jsonl`, which stores every
  raw current/voltage sample per run.

## Deviations from the protocol

**D1 — power source substituted (forced).** `/sys/class/power_supply/battery/*` is
unreadable; `cmd battery get -f current_now` × `dumpsys battery voltage` used
instead, in mA × mV rather than the assumed µA × µV. Verified against the
protocol's 0.3–0.8 W idle sanity band. No ODPM rails available as a fallback.

**D2 — airplane mode on, WiFi deliberately left up.** The protocol requires
airplane mode; the operator requires measured runs over wireless ADB. Full airplane
mode drops WiFi and removes the transport. Airplane mode is therefore enabled with
WiFi re-enabled: cellular is confirmed `POWER_OFF` and Bluetooth off, only WiFi
remains. WiFi is up during the idle baseline as well, so subtracting the baseline
removes most of its contribution; the residual is WiFi activity induced by the
sampling traffic itself.

**D3 — sampling is discrete `adb shell` invocations, not a held shell.** One
combined call per 500 ms tick returns RSS/HWM, power and thermal zones together
(~68 ms per call). Memory is sampled at 500 ms and power/thermal on alternate ticks
(~1 Hz) as specified. No shell is left open and no helper process runs on the
device, per the operator's constraint. The sampling traffic is itself a small load
on the measurement target.

**D4 — `-ngl 999` omitted.** It is a no-op on a CPU-only build. All other server
flags match Device 2 exactly: `-c 4096 -b 2048 -ub 512 --no-mmap --parallel 1
--no-webui --reasoning-format none -t <threads>`.

**D5 — `--no-mmap` is deprecated at this commit.** The build warns
`DEPRECATED: --mmap and --no-mmap are deprecated. use --load-mode mmap instead`.
The flag is still honoured; **mmap was OFF for every run**.

**D6 — thermal design restructured (operator decision).** The protocol's
"every row measured twice (cold + sustained)" was replaced, on the operator's
instruction, with: sustained = the full matrix (primary result); cold = Q4_K_M only
across {text-512, vision, audio-30s} × 3 reps with a genuine 10-minute idle before
**every** cold run (no cool-once-run-many, so no cold median is contaminated by warm
runs); plus one 20-minute continuous thermal decay curve from cold
(`thermal_decay.csv`). Rationale: the literal reading implies ~170 cooldowns ≈ 28 h
of cooling alone, and a single decay curve localises the onset of throttling better
than a cold/sustained pair. Zone temperatures are recorded at the start and end of
every run, cold and sustained.

**D7 — BF16 moved to last in the variant order.** Ordering only; no measurement
methodology changed. BF16 is the slowest and likeliest to thrash, so it is attempted
after a complete dataset exists for the other variants.

**D8 — thermal temperatures carried in `notes`.** The 26-column schema is fixed by
the protocol and has no column for temperature, so per-run start/end zone readings
are written into `notes` (`tz_start[...]` / `tz_end[...]`) and the full zone sets to
`raw_runs.jsonl`. The column set in `results.csv` is exactly as specified.

**D9 — `encoder_ms` is blank on every row.** `llama-server` does not report image or
audio encode latency separately; encode time is folded into `ttft_ms` and into the
server's `prompt_ms`. Noted per-row. (The encoder contribution is nonetheless
isolated analytically in the padded-window section below, by subtracting LLM prefill
at the independently measured text prefill rate.)

**D10 — two columns appended beyond the protocol's 26.** `avg_power_w_raw`
(the as-specified mean, so the effect of the power correction is visible per-row)
and `power_samples_used` (surviving sample count, with rows below 8 flagged
`UNRELIABLE POWER` in notes). They are appended *after* the protocol's 26 columns,
so the leading schema stays byte-compatible with Devices 1 and 2 and the three
CSVs can still be concatenated positionally.

**D11 — the measured request path is a direct TCP connection, not `adb forward`.**
`adb forward` tunnels TCP through adb's own multiplexing protocol. Measured against
the server's own `timings`, it cost 2–17% of client-side `decode_tps` even when
healthy, and when the WiFi link degraded it produced a run reporting **0.36 tps
client-side against 7.38 tps server-side** — a 95% error that would have been
indistinguishable from a genuine thermal or memory finding. `llama-server` therefore
binds `0.0.0.0` and the harness connects directly to the phone's WiFi address.
Client/server decode agreement after the change: **0.990–0.998**. The phone remains
unplugged and wireless; only the tunnel was removed.

**D12 — memory sampling stays at the protocol's 500 ms.** An attempt to slow it to
2 s, on the theory that adb round-trips were competing with the measured HTTP
stream, made delivery dramatically *worse* (client/server ratio fell to 0.444 and
0.130). The causation runs the other way — see D13. The change was reverted and the
protocol's cadence retained. Recorded here because the failed hypothesis is the
evidence for D13.

**D13 — a host-side ICMP keepalive holds the WiFi radio in active mode.** Android's
WiFi power-save lets the radio idle between requests, after which streamed chunks
are delivered in DTIM bursts rather than continuously; this inflates
`t_last − t_first` and deflates client-side `decode_tps`, which the protocol defines
client-side. A `ping -i 0.05` runs on the Mac for the duration of the session — it
touches nothing on the phone and adds no process there, consistent with the
operator's constraint. Effect: round-trip latency fell from avg 146 ms / max 489 ms
to **avg 13.7 ms / max 47 ms**, and client/server decode agreement became a stable
0.996 across runs *including* the 16 s inter-run gap that previously broke it.
Two side effects worth recording: the radio's active state is present during both
the idle baseline and the measured runs, so its power cost cancels in
`avg_power_w − idle_power_w`; and the 0 mA register sentinels disappeared entirely
(0 of 105 baseline samples, against 19 of 88 before), because the SoC no longer
enters the deep-idle state that produced them.

**D14 — `VmHWM` is reset before every run.** `VmHWM` is peak RSS since *process*
start, and one `llama-server` process serves all 30 runs of a variant block, so
without a reset each run would inherit the running maximum of every earlier run —
`audio-10s`, which executes last, would have reported `audio-30s`'s larger peak and
the memory column would have been monotonically non-decreasing within each block.
Writing `5` to `/proc/<pid>/clear_refs` resets the mark, making `peak_rss_gb` a true
per-run peak. Verified on this device before use.

**D15 — every row carries a transport self-check.** Because `decode_tps` is defined
client-side, each row records `server_decode_tps` and the client/server ratio in
notes, and any row below 0.95 is flagged `TRANSPORT-AFFECTED`. Transport
contamination is therefore visible per-row rather than assumed absent. Note that
`ttft_ms` and `total_ms` still contain some transport overhead that `decode_tps` and
`prefill_tps` do not; on audio and vision rows (TTFT ~100–160 s) this is ~1–2%, but
on text-128 (TTFT ~3 s) it is proportionally larger.

## Commands

```
# fixed artifacts verified
shasum -a 256 bench_image.jpg prompts_text.txt bench_audio_30s.wav bench_audio_10s.wav

# patch
git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp
git checkout ea63b4d
git apply --check qwen3avl-support.patch && git apply qwen3avl-support.patch

# build (see configure block above)

# staged to device
adb push <binaries+libs> /data/local/tmp/qolda/bin/
adb push <gguf files>    /data/local/tmp/qolda/models/
adb push bench_image.jpg bench_audio_*.wav prompts_text.txt /data/local/tmp/qolda/art/

# audio smoke test (see finding S1)
adb shell 'cd /data/local/tmp/qolda && LD_LIBRARY_PATH=bin bin/llama-mtmd-cli \
  -m models/Q4_K_M/Qolda-AVL-5B-Q4_K_M.gguf \
  --mmproj models/mmproj/mmproj-Qolda-AVL-5B-F16.gguf \
  --audio art/bench_audio_30s.wav \
  -p "Аудиодағы сөйлеуді сөзбе-сөз жазып шық." -t 6 -n 32 --no-mmap'

# wireless ADB, unplugged measurement transport
adb tcpip 5555 && adb connect 192.168.0.138:5555
adb shell cmd connectivity airplane-mode enable && adb shell svc wifi enable
adb shell input keyevent 26                      # screen off

# power calibration
python3 calibrate_power.py --seconds 90

# token census
python3 token_census.py

# matrix
python3 bench.py --thermal sustained --variants Q4_K_M
python3 bench.py --thermal cold
python3 bench.py --decay
python3 bench.py --thermal sustained --variants Q5_K_M,Q6_K,Q8_0 --controls
python3 bench.py --thermal sustained --variants BF16
```

Server launch (detached on-device, no shell held open):

```
cd /data/local/tmp/qolda; export LD_LIBRARY_PATH=/data/local/tmp/qolda/bin;
nohup .../llama-server -m <model> --mmproj <mmproj> --host 127.0.0.1 --port 8077 \
  -c 4096 -b 2048 -ub 512 --no-mmap --parallel 1 --no-webui \
  --reasoning-format none -t 6 > logs/<tag>.log 2>&1 < /dev/null & echo $!
```

Generation settings on every measured run: `n_predict=256`, `ignore_eos=true`,
`temperature=0.7`, `top_p=0.95`, `top_k=20`, `seed=1234`, `n_ctx=4096`,
`cache_prompt=false`, single stream, mmap off, 3 discarded warm-up requests per
server start, server restarted between variants.

---

## Primary results matrix

5 variants x 6 modes, `audio+vision` projector, `-t 6`, `thermal_state = sustained`.
Median with min-max range, three significant figures. This is the deliverable table.

| variant | mode | n | prompt_tok | ttft_ms | prefill_tps | decode_tps | decode range | peak_rss_gb | avg_power_w | energy_J/1k |
|---|---|---|---|---|---|---|---|---|---|---|
| Q4_K_M | text-128 | 5 | 128 | 2930 | 44.2 | 9.78 | 9.69–10.7 | 5.49 | 7.32 | 689 |
| Q4_K_M | text-512 | 5 | 513 | 11600 | 44.2 | 8.9 | 8.19–8.97 | 5.28 | 7.33 | 765 |
| Q4_K_M | text-2048 | 5 | 2048 | 59700 | 34.3 | 5.27 | 5.2–5.33 | 5.26 | 6.04 | 1050 |
| Q4_K_M | vision | 5 | 1101 | 161000 | 6.88 | 6.68 | 6.42–6.72 | 5.93 | 4.38 | 589 |
| Q4_K_M | audio-30s | 5 | 1540 | 135000 | 11.6 | 5.85 | 5.84–5.94 | 6.36 | 4.58 | 696 |
| Q4_K_M | audio-10s | 5 | 540 | 102000 | 5.29 | 8.14 | 8.08–8.24 | 6.53 | 4.34 | 475 |
| Q5_K_M | text-128 | 5 | 128 | 3650 | 35.8 | 8.51 | 8.21–8.57 | 5.6 | 7.39 | 809 |
| Q5_K_M | text-512 | 5 | 513 | 15000 | 34.4 | 7.31 | 6.95–7.48 | 5.49 | 7.15 | 922 |
| Q5_K_M | text-2048 | 5 | 2048 | 72300 | 28.4 | 4.81 | 4.77–4.84 | 5.49 | 6.19 | 1190 |
| Q5_K_M | vision | 5 | 1101 | 167000 | 6.6 | 5.84 | 5.82–5.94 | 6.23 | 4.59 | 706 |
| Q5_K_M | audio-30s | 5 | 1540 | 143000 | 10.8 | 5.34 | 5.29–5.38 | 6.66 | 4.95 | 841 |
| Q5_K_M | audio-10s | 5 | 540 | 106000 | 5.12 | 6.9 | 6.43–6.93 | 6.83 | 4.73 | 616 |
| Q6_K | text-128 | 5 | 128 | 4010 | 32.1 | 6.92 | 6.75–6.99 | 6.29 | 7.65 | 1030 |
| Q6_K | text-512 | 5 | 513 | 16700 | 30.8 | 6.2 | 6.15–6.21 | 6.18 | 7.33 | 1110 |
| Q6_K | text-2048 | 5 | 2048 | 77600 | 26.4 | 4.45 | 4.41–4.49 | 6.19 | 6.65 | 1380 |
| Q6_K | vision | 5 | 1101 | 170000 | 6.5 | 5.36 | 5.35–5.4 | 6.69 | 4.95 | 836 |
| Q6_K | audio-30s | 5 | 1540 | 163000 | 9.7 | 4.88 | 4.82–4.92 | 6.33 | 4.93 | 902 |
| Q6_K | audio-10s | 5 | 540 | 118000 | 4.67 | 6.13 | 6.04–6.3 | 6.5 | 4.72 | 684 |
| Q8_0 | text-128 | 5 | 128 | 2040 | 65.3 | 7.59 | 7.33–7.82 | 6.9 | 7.82 | 951 |
| Q8_0 | text-512 | 5 | 513 | 9300 | 55.9 | 6.63 | 5.91–6.74 | 6.8 | 7.6 | 1050 |
| Q8_0 | text-2048 | 5 | 2048 | 51800 | 41.4 | 4.52 | 4.37–4.7 | 4.96 | 6.46 | 1300 |
| Q8_0 | vision | 5 | 1101 | 155000 | 7.21 | 5.87 | 5.59–5.92 | 7.33 | 4.58 | 696 |
| Q8_0 | audio-30s | 5 | 1540 | 124000 | 12.6 | 5.28 | 5.17–5.42 | 7.75 | 4.89 | 834 |
| Q8_0 | audio-10s | 5 | 540 | 99800 | 5.47 | 6.82 | 6.65–6.91 | 7.92 | 4.79 | 621 |
| BF16 | text-128 | 5 | 128 | 90500 | 1.42 | 1.16 | 1.14–1.17 | 7.67 | 4.07 | 3080 |
| BF16 | text-512 | 2 | 513 | 365000 | 1.42 | 1.13 | 1.11–1.15 | 7.77 | 3.53 | 2690 |
| BF16 | text-2048 | 0 | – | N/A (not measured: battery floor reached; BF16 prefill is 1.42 tok/s, implying ~20-25 min per run) | – | – | – | – | – | – |
| BF16 | vision | 0 | – | N/A (not measured: battery floor reached; BF16 prefill is 1.42 tok/s, implying ~20-25 min per run) | – | – | – | – | – | – |
| BF16 | audio-30s | 0 | – | N/A (not measured: battery floor reached; BF16 prefill is 1.42 tok/s, implying ~20-25 min per run) | – | – | – | – | – | – |
| BF16 | audio-10s | 0 | – | N/A (not measured: battery floor reached; BF16 prefill is 1.42 tok/s, implying ~20-25 min per run) | – | – | – | – | – | – |

**BF16 coverage.** text-128 is complete at n=5 and text-512 at n=2; the remaining
four modes were not measured. This is a time/battery limit, not a model failure:
BF16 prefills at 1.42 tok/s, so a single vision or audio run would take 20-25
minutes and a full 30-run block roughly 10 hours. The seven rows collected
characterise the variant conclusively (reproducible to within 3%, see F9). The
cells are marked with that reason rather than a bare N/A.

## Supplementary rows (protocol-specified, reported separately)

These are the control and thread-sensitivity rows the protocol requested. They are
deliberately kept out of the primary matrix above because they vary a parameter
other than variant x mode.

| purpose | variant | mmproj | threads | mode | n | decode_tps | peak_rss_gb | ttft_ms |
|---|---|---|---|---|---|---|---|---|
| control (a): no projector | Q4_K_M | none | 6 | text-512 | 5 | 8.36 | 3.33 | 12800 |
| baseline for (a) | Q4_K_M | audio+vision | 6 | text-512 | 5 | 8.9 | 5.28 | 11600 |
| control (b): vision-only projector | Q4_K_M | vision-only | 6 | vision | 5 | 6.82 | 4.64 | 166000 |
| baseline for (b) | Q4_K_M | audio+vision | 6 | vision | 5 | 6.68 | 5.93 | 161000 |
| thread sensitivity -t 4 | Q4_K_M | audio+vision | 4 | text-512 | 5 | 6.49 | 5.09 | 18000 |
| thread sensitivity -t 6 (baseline) | Q4_K_M | audio+vision | 6 | text-512 | 5 | 8.9 | 5.28 | 11600 |
| thread sensitivity -t 8 | Q4_K_M | audio+vision | 8 | text-512 | 5 | 5.1 | 5.38 | 13500 |

| purpose | variant | mmproj | threads | mode | n | decode_tps | peak_rss_gb |
|---|---|---|---|---|---|---|---|
| cold (partial sample) | Q4_K_M | audio+vision | 6 | text-512 | 3 | 9.01 | 5.38 |
| cold (partial sample) | Q4_K_M | audio+vision | 6 | vision | 1 | 7.52 | 5.59 |

## Findings

Reproducibility across the primary matrix is high (e.g. Q4_K_M audio-30s decode
5.84–5.94, Q6_K text-512 6.15–6.21). No outliers were discarded; `aggregate.py`
flags any value more than 25% off its cell median and retains it.

### F1 — The Whisper encoder runs the full padded 30 s window (the headline audio result)

`encoder_ms` is not reported by `llama-server` (D9), but the encoder's contribution
can be isolated: subtract the LLM prefill cost from the server's `prompt_ms`, using
the text-only prefill rate measured independently on the same variant and thermal
state (**44.2 tok/s**, identical for text-128 and text-512).

| mode | prompt_n | prompt_ms | LLM prefill | **encoder** |
|---|---|---|---|---|
| audio-10s | 540 | 102.2 s | 12.2 s | **89.9 s** |
| audio-30s | 1540 | 133.1 s | 34.8 s | **98.3 s** |
| vision | 1101 | 160.0 s | 24.9 s | **135.1 s** |

**encoder(10 s) / encoder(30 s) = 0.915.** Three times the audio duration costs
**1.09×** the encoder time. The 10-second clip pays 89.9 s of encode against the
30-second clip's 98.3 s, so encoder cost is essentially invariant to clip length —
the model card's claim that the encoder runs the full padded 30 s mel window
regardless of input length is confirmed on this hardware.

The deployment consequence is severe and specific to CPU inference: a short
utterance has no latency advantage. A 10-second command costs ~90 seconds before
the first token. Short-utterance interactive speech is not viable on this device
class, and the cost cannot be reduced by sending shorter audio.

An independent confirmation came from the one-token token-census probes (a
different measurement, no decode contamination): encoder 67.3 s for the 10 s clip
against 64.9 s for the 30 s clip, ratio 1.04. Both measurements agree that the two
clip lengths cost the same.

Vision is worse still in absolute terms: **135.1 s** of encoder for one 1024×1024
image, the slowest single stage measured anywhere in this matrix.

### F2 — Encoder activation memory, not projector weights, is the binding constraint

Peak RSS is a true per-run figure (the kernel high-water mark is reset before every
run — see D14), so these are directly comparable:

| mode | peak_rss_gb | MemAvailable before run |
|---|---|---|
| text-2048 | 5.26 | 4.73 GB |
| text-512 | 5.28 | 4.76 GB |
| text-128 | 5.49 | 4.53 GB |
| vision | 5.93 | 4.34 GB |
| audio-30s | 6.36 | 3.92 GB |
| **audio-10s** | **6.53** | **3.63 GB** |

Loaded and idle the server sits at 5.29 GB, matching the protocol's ~5.3 GB
estimate for Q4_K_M plus the 2.04 GiB audio+vision projector plus KV. But
processing audio adds a further **~1.1 GB of transient activation memory** on top,
and vision adds ~0.6 GB. That cost is charged on top of resident weights, is
independent of LLM quantization, and — consistent with F1 — is *larger for the
10-second clip than the 30-second one*, because the padded buffer is allocated
regardless of how much audio it holds.

This reframes the protocol's expectation. The binding constraint is not the fixed
2.04 GiB of projector weights sitting in memory; it is the encoder's peak working
set during inference, which the weights-plus-KV arithmetic does not capture.

### F3 — Decode throughput halves across the context range

| prompt tokens | decode_tps |
|---|---|
| 128 | 9.78 |
| 513 | 8.90 |
| 2048 | 5.27 |

Decode falls 46% from 128 to 2048 tokens of context as KV attention cost grows.
This compounds with F1: audio-30s arrives with 1540 tokens of context *before* the
user's own prompt, so audio workloads pay both the encoder latency and the
degraded decode rate that a long context imposes.

### MemAvailable observed so far

3.63 GB (during audio-10s) to 10.53 GB (idle, no server loaded). The device
reports 15,569,104 kB (14.85 GiB) of RAM; the usable figure under load never
approached that, consistent with the protocol's warning that 16 GB nominal is not
16 GB usable.

### F4 — The device reaches a stable thermal sawtooth and does not progressively throttle

Every row records zone temperatures at the start and end of generation. Across the
Q4_K_M block's 38 minutes of back-to-back running, the device settles into a
repeating cycle — heating from ~48 °C to ~76 °C during each run and recovering to
~48 °C in the ~16–20 s gap between runs — and **throughput does not decline**:

| mode | elapsed | cpu_start | cpu_end | decode_tps |
|---|---|---|---|---|
| text-2048 run1 | 12.8 min | 47.7 | 72.7 | 5.27 |
| text-2048 run5 | 21.1 min | 50.8 | 75.9 | 5.33 |
| vision run1 | 23.2 min | 51.2 | 76.6 | 6.72 |
| vision run5 | 37.7 min | 50.8 | 74.7 | 6.68 |

The partial cold sample points the same way, and shows the penalty scales with how
long a single request keeps the CPU saturated: text-512 (~11 s of prefill) is only
**1.2%** faster cold (9.01 vs 8.90 tps), while vision (~135 s of encoder) is
**12.6%** faster cold (7.52 vs 6.68 tps). Short requests finish before the SoC
heats; long ones throttle within a single run.

**Scope limit.** What is measured here is *duty-cycled* sustained load — the
harness leaves ~16–20 s between runs, and the device visibly recovers ~28 °C in
those gaps. Genuinely continuous generation with no recovery was not measured; the
20-minute decay curve that would have covered it was not run. A reviewer asking
"what happens without the idle gaps?" is not answered by this dataset.

### F5 — Encoder cost is invariant to LLM quantization (measured, not assumed)

The same decomposition applied to two variants independently:

| variant | text prefill | encoder(10 s) | encoder(30 s) | ratio | vision encoder |
|---|---|---|---|---|---|
| Q4_K_M | 44.2 tok/s | 89.9 s | 98.3 s | **0.915** | 135.1 s |
| Q5_K_M | 35.1 tok/s | **90.1 s** | **98.7 s** | **0.913** | **135.4 s** |

Encoder times agree to within 0.3% across variants whose LLM weights differ by
16%, and the padded-window ratio replicates at 0.915 / 0.913. This is what the
architecture predicts — the Whisper and vision encoders are F16 and do not shrink
with LLM quantization — but it is here measured rather than assumed.

Encoder activation memory replicates as well: peak RSS for audio-30s minus
text-2048 is 1.10 GB on Q4_K_M and 1.17 GB on Q5_K_M.

**Deployment consequence.** For audio-30s the encoder is ~98 s of a ~135-142 s
time-to-first-token, so roughly **70% of TTFT is a fixed cost that quantization
cannot reduce**. Moving Q5_K_M -> Q4_K_M buys 22% on text-512 decode but almost
nothing on audio latency. On this device class, choosing a smaller quant is close
to irrelevant to the latency a user of the audio path actually experiences; the
only lever that matters is the encoder.

### F6 — Quantization does not monotonically predict speed on ARM CPU

| variant | prefill tok/s | decode text-128 | audio-30s TTFT | peak RSS audio-30s |
|---|---|---|---|---|
| Q4_K_M | 44.2 | 9.78 | 134.9 s | 6.36 GB |
| Q5_K_M | 35.1 | 8.51 | 143.0 s | 6.66 GB |
| Q6_K | 31.4 | 6.92 | 163.4 s | 6.33 GB |
| **Q8_0** | **60.6** | 7.59 | **124.2 s** | 7.75 GB |

**Q8_0 prefills 1.9x faster than Q6_K and 1.37x faster than Q4_K_M**, despite
being the largest quantized variant. Q8_0's 8-bit weights feed ARM integer
matrix-multiply (`i8mm`, enabled in this build via `HAVE_MATMUL_INT8`) directly,
while K-quants require per-sub-block unpacking before any arithmetic. Q8_0 also
beats Q6_K on decode in every mode measured.

Because TTFT on this device is prefill-dominated for every multimodal mode (1101
image tokens, 1540 audio tokens), the prefill advantage lands on the metric users
actually feel: **Q8_0 has the lowest audio-30s TTFT of any variant, 124.2 s
against Q4_K_M's 134.9 s and Q6_K's 163.4 s.**

**Q6_K is dominated on every axis measured** -- slower than Q8_0 at both prefill
and decode, slower than Q4_K_M at everything, and only 24% smaller than Q8_0. On
this hardware it has no operating point where it is the right choice.

The practical recommendation inverts the usual advice: on ARM CPU, pick **Q4_K_M
when memory is tight** or **Q8_0 when it is not** -- not the intermediate K-quants.

### F7 — Q8_0 exceeds resident memory and swaps to zram

Q8_0 (3.99 GiB weights + 2.04 GiB projector) does not fit resident on this device.
Measured during the Q8_0 block: `MemAvailable` fell to 2.70 GB and **~4.7 GB was
pushed into zram**; peak RSS on audio-10s reached 7.92 GB, the highest in the
dataset. The protocol predicted Q8_0 at ~7.1 GB would "fit" -- it runs, but not
resident.

This also exposes a measurement trap. **Under swap, `peak_rss_gb` moves the wrong
way.** Within the Q8_0 block peak RSS *fell* from 6.80 GB (text-512) to 4.92 GB
(text-2048) as the kernel evicted more pages -- which naively reads as *lower*
memory use, and would have made Q8_0 look lighter than Q6_K. Rows now carry
`swap_used=X->Y GB` and a `SWAP-AFFECTED` flag so the direction of the error is
visible. Swap tracking was added partway through the Q8_0 block, so its three text
modes lack the field; this is a gap in instrumentation, not a measurement, and is
not backfilled.

### Control (a) — the projector costs 1.95 GB and buys a text deployment nothing

Q4_K_M / text-512, identical in every respect except `--mmproj`:

| | peak RSS | decode tps | TTFT |
|---|---|---|---|
| with audio+vision projector | 5.28 GB | 8.90 | 11.6 s |
| **no `--mmproj`** | **3.33 GB** | 8.52 | 12.8 s |
| difference | **-1.95 GB** | ~0 (thermal) | ~0 |

Carrying the projector costs essentially its full 2.04 GiB on-disk size in
resident memory and delivers no throughput benefit to a text-only workload. On a
device where `MemAvailable` runs 9-10 GB and Q8_0 already swaps, shipping the
multimodal projector in a text-only Kazakh deployment wastes ~2 GB for nothing --
the difference between Q4_K_M sitting comfortably at 3.33 GB and occupying
5.28 GB with the encoders idle.

### F8 — Thread count must be pinned to the big cores; `-t $(nproc)` costs 43%

Q4_K_M / text-512 / sustained, n=5 per cell:

| threads | decode tps | prefill tps | TTFT | vs `-t 6` |
|---|---|---|---|---|
| 4 | 6.49 | 28.7 | 18.0 s | -27.1% |
| **6** | **8.90** | **44.2** | **11.6 s** | baseline |
| 8 | 5.10 | 38.1 | 13.5 s | **-42.7%** |

**Using all 8 cores is worse than using only 4.** The SoC is heterogeneous (1x
Cortex-X4 + 3+2x A720 big, 2x A520 little at 2.2656 GHz against the prime core's
3.3024 GHz). ggml divides work evenly across threads, so at every synchronisation
barrier the six fast cores idle waiting on two slow ones; the little cores add
latency rather than capacity.

The effect is larger on decode (-42.7%) than prefill (-14%), which fits the
mechanism: prefill is a large batched GEMM with enough work per barrier to
amortise a straggler, while decode synchronises on every single token.

**Deployment consequence.** The obvious default, `-t $(nproc)` = 8, costs 43% of
decode throughput on this device -- a larger penalty than the entire Q4_K_M to
Q8_0 quantization difference, and free to avoid. Thread count must be pinned to
the big-core count (6 here).

### F9 — BF16 runs, permanently swapped, at ~1/8 the throughput

BF16 did **not** OOM and was **not** refused. It loaded in 26.1 s and ran to
completion on every attempted run. It is nonetheless unusable.

| | BF16 | Q4_K_M | ratio |
|---|---|---|---|
| TTFT (128-token prompt) | **93,082 ms** | 2,930 ms | **32x slower** |
| decode | **1.17 / 1.16 / 1.14 tps** | 9.78 tps | **8.4x slower** |
| peak RSS | 7.87 GB | 5.49 GB | +2.4 GB |
| wall per 256-token run | 328 s | 29 s | 11x |

Memory at steady state during BF16, sampled over 3 minutes: **7.67 GB resident +
4.18 GB in zram, with 1.10 GB `MemAvailable` remaining**. `MemAvailable` before
load was 10.63 GB, so BF16 consumed ~9.5 GB. During loading, RSS oscillated
between 5.4 and 9.2 GB with swap peaking at 6.94 GB before settling. Process state
stayed `R` (computing) rather than `D` (blocked on I/O), so this is a stable
swap-bound equilibrium, not live thrashing -- which is why the numbers are
reproducible to within 3% across runs rather than erratic.

Prefill degrades far worse (32x) than decode (8.4x). That asymmetry is the
signature of a swap-bound rather than compute-bound workload: prefill must touch
every weight, and most of them are compressed in zram, while decode re-reads a
smaller working set per token.

**This is the "technically runs, unusably slow" result the protocol asked for
rather than an N/A.** At 1.17 tok/s a 256-token reply takes 3 min 39 s, on the
*shortest* prompt in the matrix. The protocol's ~10.9 GB estimate for BF16 was
essentially correct; the device offers ~10.6 GB at absolute best, with nothing
else running, screen off and airplane mode on. BF16 "fits" only in the sense that
the kernel can compress its way out of the deficit.

### Thermal note — cold block is a partial sample

The cold block was cut short by the operator for time after 4 of 9 planned runs
(text-512 n=3, vision n=1; audio-30s not run). Those rows are retained and
labelled `cold`, but the cold sample is smaller than planned and the vision cold
cell is a single run. What they show, with that caveat:

| mode | cold | sustained | cold advantage |
|---|---|---|---|
| text-512 | 9.01 tps (n=3) | 8.90 tps (n=5) | +1.2% |
| vision | 7.52 tps (n=1) | 6.68 tps (n=5) | +12.6% |

The thermal penalty scales with how long a single request keeps the CPU
saturated: text-512 spends ~11 s in prefill and finishes before the SoC heats,
while vision runs its encoder for ~135 s and throttles within a single run. The
20-minute decay curve, which would have resolved this properly, was not run.

---

*(Q6_K, Q8_0, BF16, control rows and thread sensitivity are appended as they
complete.)*
