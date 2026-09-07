# Qolda-AVL-5B deployment benchmark — Device 2: MacBook Pro / Apple M4 Pro (Metal)

All 160 measured runs completed. **No cell failed**, no variant was unsupported, and
both projectors ran on Metal. `results.csv` holds every run; this file holds the
medians, the commands, and every deviation.

## Headline device findings

1. **The audio projector runs on Metal — it does not fall back to CPU.**
   `clip_ctx: CLIP using MTL0 backend` with `projector: qwen3avl`. No per-op
   fallback warnings, no "not supported" lines. Audio compute buffer is
   183.11 MiB on MTL0 vs 1.46 MiB on CPU (the CPU side is mel-spectrogram input
   prep, which is CPU-side by design). Audio TTFT here is therefore measuring the
   same structural thing as the CUDA device, not a CPU-fallback artefact.
2. **The vision projector also runs on Metal.** `clip_ctx: CLIP using MTL0 backend`
   with `projector: qwen3vl_merger`; 355.55 MiB MTL0 vs 24.93 MiB CPU.
3. **BF16 works on Metal.** It was neither refused nor silently downgraded. It
   loads, runs, and sustains 28.5 tok/s. No F16 substitution was made or needed.

## Environment

| item | value |
|---|---|
| Machine | MacBook Pro, `Mac16,7` |
| Chip | Apple M4 Pro — 14 CPU cores (10P + 4E), 20 GPU cores |
| RAM | 24 GB unified (25,769,803,776 bytes) |
| macOS | 26.3.1 (a), build `25D771280a` |
| Metal | Metal 4 |
| Xcode | **Not installed** — Command Line Tools only; `xcrun metal` absent |
| SDK | macOS SDK 15.5 |
| clang | Apple clang 17.0.0 (`clang-1700.0.13.5`), target `arm64-apple-darwin25.3.0` |
| cmake | 4.1.0 |
| Power source | **AC power**, verified with `pmset -g batt` before the first measured run |
| Low Power Mode | disabled |
| `pmset powermode` | **2 = High Power Mode** (see Deviations) |
| Lid / display | lid open; `caffeinate -dims` held the display awake |
| Screen brightness | see Deviations — not recorded numerically |
| Ambient | ordinary office ambient, ~23 °C, machine on a hard desk surface |

Despite no full Xcode, the Metal backend built and ran: llama.cpp embeds the shader
source and compiles pipelines at runtime (`ggml_metal_library_compile_pipeline:
compiling pipeline: ...`), which needs no `metal` CLI compiler.

## llama.cpp build

- Commit: **`ea63b4d32ea1b66bdbe369be7f9443f6c00f8b31`** (`ea63b4d`), "vulkan: Support
  quantized concat (#25684)", Thu Jul 30 2026.
- Patch: `qwen3avl-support.patch`, sha256 `bb27de1efd5b`.
- **Patch applied cleanly. Zero conflicts.** `git apply --check` passed first, then
  all 8 files applied: `conversion/__init__.py`, `conversion/qwen3avl.py` (new),
  `gguf-py/gguf/constants.py`, `tools/mtmd/clip-graph.h`, `tools/mtmd/clip-impl.h`,
  `tools/mtmd/clip.cpp`, `tools/mtmd/models/whisper-enc.cpp`, `tools/mtmd/mtmd.cpp`.
- Build: clean, zero errors, `libggml-metal.dylib` produced.
- Audio smoke test before the matrix: passed — `mtmd batch encoding done in 581 ms`,
  model transcribed the clip.

## Fixed artifacts — all four hashes match the protocol

| file | sha256 | status |
|---|---|---|
| `bench_image.jpg` | `d45840444cdef3c8d81eaa73c720f78e49fd3274c510fc49fc12665c43bb2330` | match |
| `prompts_text.txt` | `bb5c5cf054819d5775533e5fb8d2914196865351b1c5144fe7bdee35759dcc09` | match |
| `bench_audio_30s.wav` | `94c91da6916aa32b9ba6cd5e602a7eb941c3b2b637f46a1744dff7a8602bbbc7` | match |
| `bench_audio_10s.wav` | `c00cefb4f2d1c942f02eedebbc21dee4ccbc90cd1b2e08a40f18f162cfa77d0c` | match |

Nothing was regenerated locally. Prompt parsing recovered **exactly 3** non-empty
prompts from the opening-marker-only format.

## Model files used

| file | GiB | sha256[:12] |
| `Qolda-AVL-5B-BF16.gguf` | 7.50 | `7df60f9052bd` |
| `Qolda-AVL-5B-Q4_K_M.gguf` | 2.33 | `4846476c27ae` |
| `Qolda-AVL-5B-Q5_K_M.gguf` | 2.69 | `193793b63208` |
| `Qolda-AVL-5B-Q6_K.gguf` | 3.08 | `d392af001fee` |
| `Qolda-AVL-5B-Q8_0.gguf` | 3.99 | `613406fad8ab` |
| `mmproj-Qolda-AVL-5B-F16.gguf` | 2.04 | `041aa58d1d39` |
| `mmproj-Qolda-AVL-5B-vision-only-F16.gguf` | 0.78 | `c06b37209e45` |
## Token counts (recorded once)

| item | measured | reference | agrees |
|---|---|---|---|
| `text-128` prompt | **128** | 128 | yes |
| `text-512` prompt | **513** | 513 | yes |
| `text-2048` prompt | **2048** | 2048 | yes |
| vision instruction | **65** | 65 | yes |
| audio instruction | **28** | 28 | yes |
| `bench_image.jpg` | **1024** (32×32 grid) | — | — |
| `bench_audio_30s.wav` | **1500** | ~1500 | yes (exactly 50 tok/s) |
| `bench_audio_10s.wav` | **500** | ~500 | yes (exactly 50 tok/s) |

**Tokenizer cross-check: PASSED.** The prompt file was generated with a Homebrew
llama.cpp build (0.3.0); re-tokenised with the patched `ea63b4d` build it yields
128 / 513 / 2048 — identical. The server-reported `prompt_n` for the text modes
also came back as exactly 128 / 513 / 2048 in every one of the 75 text runs. The
`text-512` label remains an identifier only; the prompt genuinely tokenises to
**513** and has not been "corrected" anywhere.

This resolves the "cross-check pending" item left open in the artifact-generation
notes (now preserved as `artifact_provenance.md`).

Multimodal prompt totals decompose exactly, confirming a fixed 12-token chat
template overhead: vision `1101 = 1024 + 65 + 12`; audio-30s `1540 = 1500 + 28 + 12`;
audio-10s `540 = 500 + 28 + 12`.

## Median results — one row per variant × mode

Median of 5 runs, min–max range shown for TTFT. Three significant figures.
`peak_rss_gb` is **GiB**. `peak_vram_gb` is `unified (no discrete VRAM)` on every
row — the single unified figure is in `peak_rss_gb` only, never duplicated.

| variant | mmproj | mode | prompt_tok | ttft_ms (median) | ttft range | prefill_tps | decode_tps | peak_rss_gb | avg_power_w | energy_J/1k_tok | n |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BF16 | audio+vision | text-128 | 128 | 155 | 154–156 | 833 | 28.5 | 10.2 | 18.7 | 633 | 5 |
| BF16 | audio+vision | text-512 | 513 | 611 | 610–612 | 842 | 28.4 | 10.3 | 19.3 | 658 | 5 |
| BF16 | audio+vision | text-2048 | 2048 | 2460 | 2460–2460 | 833 | 27.6 | 10.2 | 22.2 | 780 | 5 |
| BF16 | audio+vision | vision | 1101 | 2160 | 2160–2170 | 514 | 28.1 | 10.7 | 21.5 | 742 | 5 |
| BF16 | audio+vision | audio-30s | 1540 | 2350 | 2350–2430 | 666 | 27.9 | 10.5 | 21.6 | 750 | 5 |
| BF16 | audio+vision | audio-10s | 540 | 1150 | 1140–1150 | 484 | 28.4 | 10.7 | 20.2 | 686 | 5 |
| Q8_0 | audio+vision | text-128 | 128 | 157 | 155–158 | 825 | 50.4 | 7.7 | 22.7 | 437 | 5 |
| Q8_0 | audio+vision | text-512 | 513 | 615 | 615–616 | 837 | 49.8 | 7.7 | 23.8 | 464 | 5 |
| Q8_0 | audio+vision | text-2048 | 2048 | 2530 | 2530–2540 | 809 | 47.4 | 7.7 | 26.2 | 536 | 5 |
| Q8_0 | audio+vision | vision | 1101 | 2200 | 2190–2250 | 505 | 48.9 | 7.97 | 25.8 | 514 | 5 |
| Q8_0 | audio+vision | audio-30s | 1540 | 2410 | 2410–2470 | 650 | 48.2 | 8.26 | 26.1 | 527 | 5 |
| Q8_0 | audio+vision | audio-10s | 540 | 1160 | 1160–1160 | 476 | 49.7 | 8.52 | 24.5 | 479 | 5 |
| Q6_K | audio+vision | text-128 | 128 | 166 | 165–168 | 781 | 61.3 | 6.63 | 24.3 | 387 | 5 |
| Q6_K | audio+vision | text-512 | 513 | 648 | 647–649 | 795 | 60.5 | 6.63 | 25.3 | 407 | 5 |
| Q6_K | audio+vision | text-2048 | 2048 | 2680 | 2680–2680 | 765 | 57 | 6.63 | 28.3 | 484 | 5 |
| Q6_K | audio+vision | vision | 1101 | 2290 | 2290–2290 | 485 | 59.1 | 7.21 | 27.5 | 453 | 5 |
| Q6_K | audio+vision | audio-30s | 1540 | 2530 | 2530–2560 | 618 | 58.2 | 7.51 | 27.9 | 468 | 5 |
| Q6_K | audio+vision | audio-10s | 540 | 1210 | 1210–1220 | 455 | 60.3 | 7.77 | 26 | 421 | 5 |
| Q5_K_M | audio+vision | text-128 | 128 | 176 | 175–176 | 737 | 60.6 | 6.24 | 28.2 | 453 | 5 |
| Q5_K_M | audio+vision | text-512 | 513 | 685 | 684–686 | 751 | 59.8 | 6.24 | 28.7 | 468 | 5 |
| Q5_K_M | audio+vision | text-2048 | 2048 | 2830 | 2830–2830 | 725 | 56.3 | 6.25 | 30.7 | 532 | 5 |
| Q5_K_M | audio+vision | vision | 1101 | 2360 | 2360–2370 | 470 | 55.5 | 6.83 | 29.9 | 527 | 5 |
| Q5_K_M | audio+vision | audio-30s | 1540 | 2640 | 2630–2680 | 593 | 58.1 | 7.12 | 30.5 | 510 | 5 |
| Q5_K_M | audio+vision | audio-10s | 540 | 1250 | 1250–1250 | 442 | 60 | 7.39 | 29.2 | 475 | 5 |
| Q4_K_M | audio+vision | text-128 | 128 | 163 | 162–164 | 793 | 75.8 | 5.32 | 24.3 | 312 | 5 |
| Q4_K_M | audio+vision | text-512 | 513 | 635 | 635–636 | 811 | 74.2 | 5.32 | 25.1 | 328 | 5 |
| Q4_K_M | audio+vision | text-2048 | 2048 | 2640 | 2640–2690 | 776 | 68.7 | 5.33 | 28.9 | 410 | 5 |
| Q4_K_M | audio+vision | vision | 1101 | 2260 | 2260–2320 | 491 | 72.3 | 5.95 | 28.1 | 379 | 5 |
| Q4_K_M | audio+vision | audio-30s | 1540 | 2500 | 2490–2500 | 627 | 70.7 | 6.25 | 28.2 | 389 | 5 |
| Q4_K_M | audio+vision | audio-10s | 540 | 1200 | 1200–1200 | 462 | 74.2 | 6.52 | 26.5 | 348 | 5 |
| Q4_K_M | none | text-512 | 513 | 635 | 635–636 | 811 | 74.5 | 3.6 | 25.9 | 338 | 5 |
| Q4_K_M | vision-only | vision | 1101 | 2260 | 2260–2280 | 492 | 72.5 | 4.81 | 28.5 | 384 | 5 |
Full per-run data, including the retained outliers, is in `results.csv` (160 rows).

## The padded-window property — confirmed

The model card states the Whisper encoder runs on the full padded 30 s mel window
regardless of clip length. **This is true on this device, and it was measured two
independent ways.**

**Direct encoder measurement** (`llama-mtmd-cli -v`, Q4_K_M, 5 runs each):

| clip | audio tokens | encoder_ms median | range |
|---|---|---|---|
| `bench_audio_10s.wav` | 500 | **458** | 457–475 |
| `bench_audio_30s.wav` | 1500 | **460** | 459–463 |

A 0.4 % difference for 3× the audio content. The encoder does the same work either
way. Corroborated by the startup log, which reserves the padded window for both
clips: `get_dummy_batch: warmup with audio size = 3000` (3000 mel frames = 30 s).

**Independent confirmation from server timings alone.** For BF16, solving
`ttft = encoder + prompt_n / prefill_rate` with the measured text prefill rate of
833 tok/s:

- audio-30s: 2350 ms − 1540/833 s ⇒ encoder ≈ **501 ms**
- audio-10s: 1150 ms − 540/833 s ⇒ encoder ≈ **502 ms**

The two agree to 1 ms, from data that never touched `llama-mtmd-cli`.

**What this means, stated plainly:** short-audio latency does **not** improve at the
encoder. It improves only because a 10 s clip contributes 500 audio tokens to the
LLM prefill instead of 1500. On Q4_K_M, audio-10s TTFT (1200 ms) is roughly half
audio-30s (2500 ms), and every millisecond of that saving comes from LLM prefill,
not from the Whisper encoder. A deployment that chops audio into short chunks pays
the full ~460 ms encoder cost on *every* chunk.

Vision encoder, for reference: **836 ms** median (835–838, 5 runs).

## Supplementary control rows (Q4_K_M, 5 runs each)

**(a) `text-512` with no `--mmproj` at all** — isolates the cost of carrying the
projector in a text-only deployment:

| | peak_rss_gb (GiB) | decode_tps | ttft_ms |
|---|---|---|---|
| with audio+vision projector | 5.32 | 74.2 | 635 |
| `mmproj_variant = none` | **3.60** | 74.5 | 635 |
| **difference** | **1.72 GiB (1.85 GB)** | none | none |

Carrying the audio+vision projector in a text-only deployment costs **1.72 GiB of
resident memory and buys nothing** — TTFT and decode throughput are identical
(635 ms both; 74.2 vs 74.5 tok/s is within run-to-run noise). A text-only
deployment should not load it.

**(b) `vision` with the vision-only projector** — quantifies the audio branch:

| | peak_rss_gb (GiB) | decode_tps | ttft_ms |
|---|---|---|---|
| audio+vision projector (2.04 GiB file) | 5.95 | 72.3 | 2260 |
| vision-only projector (0.78 GiB file) | **4.81** | 72.5 | 2260 |
| **difference** | **1.14 GiB (1.22 GB)** | none | none |

The measured resident penalty for carrying the audio branch is **1.14 GiB**, against
a 1.26 GiB difference in file size — consistent, and slightly below the ~1.4 GB the
protocol anticipated. Vision performance is unaffected.

## Memory fit — every variant fitted, as predicted

KV cache verified from GGUF metadata rather than assumed: 36 layers × 8 KV heads ×
128 head dim × 2 (K+V) × 4096 ctx × 2 B = **576 MiB = 0.563 GiB**, matching the
protocol's ~0.6 GB estimate. Confirmed at runtime:
`llama_kv_cache: MTL0 KV buffer size = 576.00 MiB`.

| variant | predicted total | measured peak RSS (text) | fits |
|---|---|---|---|
| BF16 | ~10.9 GB | 10.2 GiB (11.0 GB) | yes |
| Q8_0 | ~7.1 GB | 7.70 GiB (8.27 GB) | yes |
| Q6_K | ~6.1 GB | 6.63 GiB (7.12 GB) | yes |
| Q5_K_M | ~5.7 GB | 6.24 GiB (6.70 GB) | yes |
| Q4_K_M | ~5.3 GB | 5.32 GiB (5.71 GB) | yes |

Measured peaks run consistently ~0.5–1.0 GB above the estimate, which is the
compute buffers (301.75 MiB MTL0 + 29.02 MiB CPU for the LLM, plus the projector's
355.55/183.11 MiB) that the estimate omitted. **No cell was memory-limited and no
`N/A` cell exists in this run.**

## Notable throughput observation

**Q6_K decodes faster than Q5_K_M despite being the larger file** — in all six
modes, though the margin varies and is not always outside the noise floor:
text-128 +1.16 %, text-512 +1.17 %, text-2048 +1.24 %, vision +6.49 %,
audio-10s +0.50 %, audio-30s +0.17 %. The three text margins and the vision margin
are outside the ≤0.66 % within-cell variation and are real; the two audio margins
are within it and should be read as "no worse", not "faster". On Metal the K-quant dequant
path for Q6_K is cheaper than Q5_K_M's, and at this size the model is not
bandwidth-bound enough for the 0.39 GiB size difference to win it back. Q5_K_M is
therefore the *worst* of the two on this device: bigger latency, lower throughput,
and only 0.39 GiB saved. This is a speed observation only — quality is not measured
here; the model card's perplexity/KLD/top-1 numbers govern that trade-off.

## Power and energy

- Boundary: **`SoC package (powermetrics)`** — `CPU Power` + `GPU Power` summed.
- **This excludes the display and DRAM rails**, and excludes ANE (unused here).
- Idle baseline before the first run: **0.600 W** (60 s, 563 samples). This is the
  value used in every `energy_j_per_1k_tok` computation.
- Idle baseline after the last run: 0.719 W — **contaminated**, see Deviations.
  A clean quiescent re-measure immediately after gave **0.572 W**, in line with the
  opening baseline, so there is no evidence of thermal drift across the session.
- `energy_j_per_1k_tok = (avg_power_w − idle_power_w) × decode_seconds / generated_tokens × 1000`

Energy per 1k tokens tracks quantisation cleanly: BF16 633–780 J, Q8_0 437–536 J,
Q6_K 387–484 J, Q5_K_M 453–532 J, Q4_K_M **312–410 J** — Q4_K_M is roughly **2× more
energy-efficient than BF16** for identical output length.

## Generation settings and the use of `ignore_eos`

`n_predict = 256`, `ignore_eos = true`, `temperature = 0.7`, `top_p = 0.95`,
`top_k = 20`, `seed = 1234`, `n_ctx = 4096`, batch size 1 (single stream),
`cache_prompt = false`, `--no-mmap` (**mmap was OFF for every run**; recorded as
`mmap=off` in each row's notes), `-ngl 999`.

**`ignore_eos` was used on every run and every run emitted exactly 256 tokens.**
`gen_tokens = 256` in all 160 rows. The base model is Qwen3-VL-4B-**Thinking**, which
emits reasoning tokens before its answer and can loop; fixing the generation length
makes every throughput window identical by construction.

**These are speed measurements, not quality measurements.** No output quality was
evaluated, scored, or inspected beyond confirming the audio path produced Kazakh
transcription text during the smoke test. The model card provides perplexity, KLD
and top-1 agreement for every quant.

## Exact commands run

Build:
```bash
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
git checkout ea63b4d
git apply --check -v ../qwen3avl-support.patch   # passed
git apply -v ../qwen3avl-support.patch           # all 8 files clean
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j --target llama-server llama-mtmd-cli llama-tokenize
```

Model download:
```bash
hf download issai/Qolda-AVL-5B-GGUF --local-dir models --exclude "imatrix/*"
```

Audio smoke test (before the matrix):
```bash
llama.cpp/build/bin/llama-mtmd-cli \
  -m models/Q4_K_M/Qolda-AVL-5B-Q4_K_M.gguf \
  --mmproj models/mmproj/mmproj-Qolda-AVL-5B-F16.gguf \
  --audio bench_audio_30s.wav \
  -p "Аудиодағы сөйлеуді сөзбе-сөз жазып шық." \
  -ngl 999 -n 24 --temp 0.7 --top-p 0.95 --top-k 20 --seed 1234 -c 4096 --no-mmap
```

Tokenizer cross-check:
```bash
llama.cpp/build/bin/llama-tokenize -m models/Q4_K_M/Qolda-AVL-5B-Q4_K_M.gguf \
  -f /tmp/tk_PROMPT_512.txt --no-bos --show-count
```

Server, started once per (variant × mmproj_variant) and killed between them:
```bash
llama.cpp/build/bin/llama-server \
  -m <variant.gguf> --mmproj <mmproj.gguf> \
  --host 127.0.0.1 --port 8077 \
  -ngl 999 -c 4096 -b 2048 -ub 512 \
  --no-mmap --parallel 1 --no-webui --reasoning-format none
```

Power logger (single persistent process spanning the whole matrix):
```bash
sudo powermetrics --samplers cpu_power,gpu_power -i 200 > power.log
```

Encoder / padded-window measurement:
```bash
llama.cpp/build/bin/llama-mtmd-cli -m models/Q4_K_M/Qolda-AVL-5B-Q4_K_M.gguf \
  --mmproj models/mmproj/mmproj-Qolda-AVL-5B-F16.gguf \
  --audio bench_audio_10s.wav -p "Аудиодағы сөйлеуді сөзбе-сөз жазып шық." \
  -ngl 999 -n 1 --seed 1234 -c 4096 -v
```

Harness: `bench.py` + `bench_lib.py` (drivers), `aggregate.py` (medians),
`parse_prompts.py` (marker parsing). Raw per-run records in `raw_runs.jsonl`.

## Harness behaviour

Per protocol: server started per variant and **restarted between variants** (never
two variants from one process); readiness polled on `/health`; **3 warm-up requests
discarded per mode**; 5 measured runs per cell; `stream=true`;
`ttft_ms` = send → first token chunk; `decode_tps = (generated − 1) / (t_last − t_first)`;
`prefill_tps = prompt_n / prompt_ms` from the server `timings` object; raw
`prompt_n`, `prompt_ms`, `predicted_n`, `predicted_ms` kept in `raw_runs.jsonl`;
memory sampled at 200 ms across the request window (peak retained); power averaged
over that window only; `vm_stat` captured before and after every run.

**Thermal:** before the first measured run of each variant the harness generated
continuously for 3 minutes (19–32 requests depending on variant) so clocks settled.
Every row is `thermal_state = "sustained"`.

## Swap and compression flags — 25 rows flagged, 3 genuinely affected

`vm_stat` deltas are **system-wide, not per-process**, so they include unrelated OS
activity. Reporting honestly:

- **3 rows of 160 saw real page-outs to disk**, all BF16 audio (the largest working
  set at ~10.5 GiB): audio-10s ×2 (max 15,692 pages ≈ 257 MB) and audio-30s ×1
  (9,088 pages ≈ 149 MB). Measured cost: decode 28.2/28.3 vs 28.4 tok/s for clean
  runs in the same cell (audio-10s), and 27.8 vs 27.9 (audio-30s) — a 0.4–0.7 %
  reduction. **These rows are flagged `SWAP-AFFECTED` and retained, not discarded.**
- **22 further rows saw memory compression with `swapout = 0`** — nothing reached
  disk. Within-cell decode variation for these is ≤ 0.5 %, and the most variable
  cells in the entire dataset (CV up to 0.66 %) are ones with *no* flag at all.
  There is no measurable throughput impact, and their notes say so.

No outlier was removed. Every one of the 160 runs is in `results.csv`.

## Deviations from the protocol — complete list

1. **`pmset powermode = 2` (High Power Mode) was retained**, on your explicit
   instruction. Low Power Mode is disabled as the protocol requires, so this is
   compliant as written, but High Power Mode is a **non-default profile** that
   raises sustained clocks and fan speed. If the CUDA and Windows devices ran stock
   profiles, this Mac's numbers are best-case and not strictly comparable. Flagging
   it here rather than burying it.
2. **`encoder_ms` is blank in every CSV row.** `llama-server` does not report encode
   latency at any verbosity available: `-lv 1` suppresses all output, and `-v`
   emits per-kernel debug that would itself distort the timings. Per protocol the
   column is left blank and each row notes *"encoder_ms folded into ttft_ms"*.
   Encoder latency was instead measured separately with `llama-mtmd-cli -v` and is
   reported in the padded-window section above — **kept out of the CSV so the two
   sources are never mixed within a mode.**
3. **Text modes used the raw `/completion` endpoint; vision and audio used
   `/v1/chat/completions`.** The protocol mandates the OpenAI-compatible endpoint
   for audio only. Text was sent as the bare prompt body (as instructed) so that
   `prompt_n` is directly comparable to 128/513/2048 without chat-template padding.
   Had text gone through the chat endpoint, `prompt_n` would have read ~140/525/2060
   and the tokenizer cross-check would have been impossible to state cleanly.
4. **`--reasoning-format none` was added to the server.** Without it, llama-server
   routes this Thinking checkpoint's `<think>` output into a separate
   `reasoning_content` stream field; a naive reader sees zero content chunks and
   TTFT would be mismeasured. This flag keeps reasoning tokens in `content`. It
   changes response formatting only, not token count or compute — `gen_tokens` is
   256 everywhere either way.
5. **Server flags beyond the protocol:** `-b 2048 -ub 512 --parallel 1 --no-webui`.
   `--parallel 1` enforces the single-stream requirement; `--no-webui` avoids
   serving the UI; batch sizes are llama.cpp defaults made explicit.
6. **`llama-server` accepted `input_audio` natively — the `llama-mtmd-cli` fallback
   path was never needed.** No row carries `timings from llama-mtmd-cli`.
7. **The closing idle baseline (0.719 W) is contaminated.** I ran two CSV
   verification commands during its 60 s window. A clean quiescent re-measure taken
   immediately after gave **0.572 W** against the 0.600 W opening baseline. Energy
   figures use the opening baseline, which is the protocol-specified one, so no
   result depends on the contaminated value.
8. **`powermetrics` timestamps have 1-second resolution**, so slicing the log to a
   request window quantises the boundary by up to ±1 s. Runs are 3.4–9 s long, so
   each window still contains 15–45 samples at the required 200 ms cadence, but
   `avg_power_w` carries a corresponding edge uncertainty.
9. **`peak_rss_gb` is reported in GiB** (binary), matching the protocol's own "size
   in GiB" convention for files. Multiply by 1.074 for decimal GB.
10. **Memory was measured with `ps rss` sampled at 200 ms**, per the protocol's
    allowance. `footprint` is available on this machine but is too slow to sustain a
    200 ms cadence. The Activity Monitor "Memory" column was **not** used anywhere.
11. **The optional battery repeat set was not run.** The protocol lists it as "if
    time allows", and it needs someone to physically unplug AC. Not done; happy to
    run it as a separate `thermal_state = "sustained (battery)"` set on request.
12. **Screen brightness is not recorded numerically.** macOS 26 exposes no
    user-facing brightness percentage without full Xcode/private APIs. The raw
    IORegistry value during the run was `IOMFBBrightnessLevel = 9269290` against
    `limit_max_physical_brightness = 104857600`. Brightness was held fixed for the
    entire session and never touched. The display was kept awake with
    `caffeinate -dims` because the system default `displaysleep` was 2 minutes,
    which would otherwise have blanked the screen mid-matrix and changed the power
    baseline.
13. **A passwordless sudoers rule was added for `powermetrics`**
    (`/etc/sudoers.d/qolda-powermetrics`) so the sampler could run unattended.
    **Remove it when you are done:** `sudo rm /etc/sudoers.d/qolda-powermetrics`.
14. **The pre-existing `summary.md` was preserved as `artifact_provenance.md`**
    rather than overwritten. It documented how the prompts and audio artifacts were
    generated and is not reproducible from this run.
15. **No full Xcode on this machine** (Command Line Tools only). The protocol asks
    for the Xcode and Metal versions; Xcode is absent, SDK is 15.5, Metal support is
    Metal 4. This did not prevent the Metal backend from building or running.

## Reproduction

```bash
python3 bench.py                 # full matrix -> results.csv
python3 bench.py Q4_K_M          # single variant
python3 aggregate.py             # median table
```
