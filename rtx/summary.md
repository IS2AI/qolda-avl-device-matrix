# Qolda-AVL-5B-GGUF Benchmark — Device 1: Windows / RTX 4090 Mobile (CUDA)

Model: `issai/Qolda-AVL-5B-GGUF`. Full results in `results.csv` (160 rows, 3 sig figs
where applicable, no aggressive rounding). This file is the median table, exact
commands, environment, artifact hashes, and every deviation from the protocol.

**Speed measurements only.** `ignore_eos=true` with a fixed `n_predict=256` was used
on every request so throughput windows are identical by construction regardless of
when/whether the Qwen3-VL-4B-Thinking base model would naturally stop or loop. No
output-quality judgment was made or attempted; the model card is the source for
perplexity/KLD/top-1 agreement per quant.

## Median results (n=5 per cell, min–max in parentheses)

All primary rows: `mmproj_variant = audio+vision`, `-ngl 999` (full offload confirmed
for every variant — no partial-offload rows), `--parallel 1`, `n_ctx = 4096`,
`thermal_state = sustained`.

| variant | mode | prompt_n | ttft_ms | decode_tps | prefill_tps | peak_vram_gb |
|---|---|---|---|---|---|---|
| BF16 | text-128 | 138 | 248.6 (231.8–275.1) | 49.03 (48.77–49.15) | 1144.1 | 12.291 |
| BF16 | text-512 | 523 | 314.0 (289.2–393.1) | 49.07 (48.62–49.62) | 3042.3 | 12.291 |
| BF16 | text-2048 | 2058 | 643.8 (627.9–691.1) | 48.00 (47.65–48.40) | 4152.6 | 12.291 |
| BF16 | vision | 1101 | 1364.5 (1178.8–2718.9)* | 48.77 (47.81–49.16) | 1166.0 | 12.434 |
| BF16 | audio-30s | 1540 | 1815.7 (1744.6–2339.1)* | 48.29 (47.97–48.90) | 1784.1 | 12.473 |
| BF16 | audio-10s | 540 | 1250.9 (1158.9–2004.9)* | 48.67 (48.43–49.65) | 1117.9 | 12.473 |
| Q8_0 | text-128 | 138 | 254.9 (200.6–321.6) | 70.75 (67.60–73.52) | 1060.2 | 8.789 |
| Q8_0 | text-512 | 523 | 374.2 (300.4–417.7) | 72.18 (69.59–73.04) | 2681.5 | 8.789 |
| Q8_0 | text-2048 | 2058 | 629.4 (625.1–736.9) | 69.11 (67.25–69.76) | 4195.2 | 8.789 |
| Q8_0 | vision | 1101 | 1319.4 (1185.2–3037.4)* | 69.00 (68.87–72.39) | 1251.3 | 8.916 |
| Q8_0 | audio-30s | 1540 | 1860.6 (1726.5–2522.3)* | 69.15 (66.80–70.41) | 1685.8 | 8.957 |
| Q8_0 | audio-10s | 540 | 1291.4 (1227.0–1694.0)* | 70.18 (69.32–71.80) | 1099.8 | 8.957 |
| Q6_K | text-128 | 138 | 214.1 (206.2–260.1) | 80.22 (79.95–82.07) | 1361.2 | 7.859 |
| Q6_K | text-512 | 523 | 377.7 (312.1–526.9) | 79.54 (77.37–80.52) | 2396.0 | 7.859 |
| Q6_K | text-2048 | 2058 | 675.7 (631.8–699.9) | 75.33 (74.12–76.45) | 3840.0 | 7.859 |
| Q6_K | vision | 1101 | 1280.6 (1172.9–2798.1)* | 77.58 (73.81–79.00) | 1283.3 | 8.000 |
| Q6_K | audio-30s | 1540 | 1996.6 (1784.3–2350.3)* | 75.40 (74.56–79.55) | 1602.4 | 8.041 |
| Q6_K | audio-10s | 540 | 1320.2 (1082.4–2056.3)* | 77.64 (75.16–79.73) | 1070.3 | 8.041 |
| Q5_K_M | text-128 | 138 | 263.9 (240.3–375.7) | 84.30 (81.82–85.32) | 1233.6 | 7.471 |
| Q5_K_M | text-512 | 523 | 349.3 (330.7–540.1) | 86.77 (80.78–88.59) | 2640.3 | 7.471 |
| Q5_K_M | text-2048 | 2058 | 649.9 (631.1–659.0) | 82.43 (81.43–84.26) | 4059.7 | 7.471 |
| Q5_K_M | vision | 1101 | 1433.9 (1196.9–2949.3)* | 82.03 (80.29–84.80) | 1203.8 | 7.611 |
| Q5_K_M | audio-30s | 1540 | 1803.4 (1704.3–2786.2)* | 83.12 (75.08–84.42) | 1749.8 | 7.654 |
| Q5_K_M | audio-10s | 540 | 1117.0 (1089.5–1784.8)* | 86.41 (85.94–87.54) | 1266.5 | 7.654 |
| Q4_K_M | text-128 | 138 | 242.6 (224.8–271.5) | 91.40 (90.27–94.53) | 1300.7 | 7.106 |
| Q4_K_M | text-512 | 523 | 375.8 (339.6–414.6) | 93.87 (90.56–94.58) | 2577.4 | 7.106 |
| Q4_K_M | text-2048 | 2058 | 645.9 (607.9–715.7) | 89.55 (85.99–90.80) | 4018.3 | 7.106 |
| Q4_K_M | vision | 1101 | 1366.4 (1212.0–2879.7)* | 88.86 (81.87–91.87) | 1226.5 | 7.246 |
| Q4_K_M | audio-30s | 1540 | 1846.0 (1644.0–2314.4)* | 89.04 (88.07–92.25) | 1693.7 | 7.289 |
| Q4_K_M | audio-10s | 540 | 1245.5 (1068.4–1735.0)* | 90.82 (89.90–93.62) | 1144.4 | 7.289 |

`*` = the max of this cell's range is `run_idx=1`; see **Cold-start artifact** below —
kept per "do not discard outliers," but not representative of steady state.

`gen_tokens = 256` on all 160/160 rows (verified). Zero request failures.

### Control rows (Q4_K_M only, n=5)

| variant | mmproj_variant | mode | ttft_ms med | decode_tps med | peak_vram_gb |
|---|---|---|---|---|---|
| Q4_K_M | none | text-512 | 358.0 (305.4–418.6) | 93.90 (89.68–110.28) | 4.549 |
| Q4_K_M | vision-only | vision | 1082.6 (920.9–1227.6) | 89.96 (88.45–99.54) | 5.785 |

- **(a) no mmproj vs audio+vision** (both text-512): 7.106 GiB → 4.549 GiB, i.e. the
  audio+vision projector (2.2 GB on disk) costs **≈2.56 GiB** of VRAM in this
  deployment shape.
- **(b) vision-only vs audio+vision** (both `vision` mode): 7.246 GiB → 5.785 GiB,
  i.e. the audio branch specifically costs **≈1.46 GiB** — close to the protocol's
  stated "~1.4 GB" estimate for carrying the audio branch.
- Control (a)'s decode_tps max (110.28) is a single-run anomaly (likely a scheduler
  hiccup on the OS side, not a device effect); kept per no-discard policy.

## Findings

### 1. Fixed CUDA-context/compute-graph VRAM overhead (~2.57 GiB, constant across all quants)

GGUF metadata (`qwen3vl.*`, verified via `gguf_dump.py`, not trusted from the
protocol's placeholder): `block_count=36`, `attention.head_count=32`,
`attention.head_count_kv=8`, `embedding_length=2560` → head_dim=80, GQA 8 KV heads.
Computed f16 KV-cache budget at `n_ctx=4096`, single slot:

```
2 (K+V) × 36 layers × 8 kv_heads × 80 head_dim × 4096 ctx × 2 bytes = 0.352 GiB
```

(The protocol's placeholder of "~0.6 GB" was on the high side; 0.352 GiB is the
verified figure for this architecture.)

Comparing `weights_on_disk + mmproj(2.043 GiB) + kv(0.352 GiB)` against measured
peak VRAM:

| variant | weights | naive estimate | measured peak | delta |
|---|---|---|---|---|
| BF16 | 7.498 GiB | 9.893 GiB | 12.473 GiB | **2.580 GiB** |
| Q8_0 | 3.986 GiB | 6.381 GiB | 8.957 GiB | **2.576 GiB** |
| Q6_K | 3.079 GiB | 5.474 GiB | 8.041 GiB | **2.567 GiB** |
| Q5_K_M | 2.691 GiB | 5.086 GiB | 7.654 GiB | **2.568 GiB** |
| Q4_K_M | 2.326 GiB | 4.720 GiB | 7.289 GiB | **2.569 GiB** |

The delta is constant to within 13 MiB across a weight range spanning 2.3–7.5 GiB.
This is CUDA context + compute-graph scratch buffers (attention workspace, vision
ViT and Whisper-encoder activation buffers) — independent of quantization level,
as expected since it scales with activation dimensions/context, not weight size.
**Deployment planning should budget a fixed ~2.6 GiB on top of weights+projector+KV,
not a quant-scaled figure.**

### 2. Padded-window property confirmed: 10s and 30s audio clips have similar latency

Audio token counts scale with real audio duration (10s ≈ 512 tokens, 30s ≈ 1512
tokens — see below), consistent with the patch's "only tokens covering real samples
are emitted." But `ttft_ms` does **not** scale 3× for 3× the duration — it rises
only ~1.4–1.6× across every variant:

| variant | audio-10s ttft_ms | audio-30s ttft_ms | ratio |
|---|---|---|---|
| BF16 | 1250.9 | 1815.7 | 1.45× |
| Q8_0 | 1291.4 | 1860.6 | 1.44× |
| Q6_K | 1320.2 | 1996.6 | 1.51× |
| Q5_K_M | 1117.0 | 1803.4 | 1.61× |
| Q4_K_M | 1245.5 | 1846.0 | 1.48× |

This confirms the model card's claim: the Whisper encoder runs on the full padded
30 s mel window regardless of clip length, so most of the audio-request latency is
fixed encoder compute; the remaining ~45–60% increase for 3× duration is the LLM
prefill over the extra ~1000 audio tokens. **Short-audio latency does not improve
proportionally with shorter input** — a 10 s clip is not ~3× faster than 30 s,
only ~1.5× faster.

`encoder_ms` is blank in the CSV for all rows: neither `/completion`-style nor
`/v1/chat/completions` timings report a separate encode-latency field on this
build; encode time is folded into `ttft_ms`/`prompt_ms`, as anticipated by the
protocol's fallback instruction.

### 3. Tokenizer cross-check: `ea63b4d` diverges from the Homebrew-build reference by a consistent +2 tokens

The prompt file was generated with a different (Homebrew) llama.cpp build. Raw
prompt-body tokenization (`llama-tokenize --no-bos`, verified 3 independent ways:
`-p`, `-f`, `--stdin`) on this build gives:

| label | Homebrew reference | `ea63b4d` actual | delta |
|---|---|---|---|
| text-128 | 128 | 130 | +2 |
| text-512 | 513 | 515 | +2 |
| text-2048 | 2048 | 2050 | +2 |

A consistent +2-token divergence on every prompt — a real tokenizer-version
difference, not noise. The server-reported `prompt_n` in `results.csv` (138 / 523 /
2058) is a further consistent +8 tokens higher than the raw-body counts above, from
the qwen3vl chat template wrapper (`<|im_start|>user\n...<|im_end|>\n<|im_start|>
assistant\n<think>\n`) added around the raw text — also verified consistent across
all three prompt sizes. **The CSV holds the server-reported `prompt_n` as ground
truth; the mode labels (`text-128`/`text-512`/`text-2048`) are identifiers only,**
per protocol instructions — no values were "corrected."

### 4. Cold-start artifact: first vision/audio request per server session is slower

Every one of the 5 variants shows `run_idx=1` in `vision` mode at ~2.1–2.5× the
median `ttft_ms` of runs 2–5 (e.g. Q8_0: 3037 ms vs a 1185–1319 ms range for runs
2–5), and a smaller but still consistent ~1.3–1.7× elevation on `run_idx=1` for both
audio modes. **Root cause:** the protocol's 3 warm-up requests used only the
`text-128` prompt (no explicit per-modality warmup was specified), so the first
*vision* or *audio* request in each server session pays a one-time CUDA
kernel/graph initialization cost for that modality's encoder path that is not
amortized by text-only warmup. This is reproducible and identical in shape across
all 5 variants (i.e., a real device/software effect, not measurement noise). Per
protocol these outliers are **kept, not discarded**, in `results.csv`; the median
figures above therefore run slightly high for vision/audio versus true steady-state
(a median over runs 2–5 only would be ~150–250 ms lower for vision, ~100–150 ms
lower for audio). **Recommendation for the Mac/Android runs:** add a per-modality
warm-up request if a cleaner steady-state figure is wanted; this run did not, to
keep methodology identical to what was specified.

### 5. Token counts (recorded once)

- Image tokens for `bench_image.jpg` (1024×1024): prompt_n(vision) − 65
  (instruction) = **1036** tokens. Consistent with the server's own startup warning
  ("Qwen-VL models require at minimum 1024 image tokens").
- Audio tokens: 30 s clip → prompt_n − 28 = **1512**; 10 s clip → prompt_n − 28 =
  **512**. Both close to the protocol's "~50 tokens/second" expectation (50.4/s and
  51.2/s respectively). Note: these are derived as `prompt_n − instruction_tokens`;
  if the chat template adds any wrapper tokens specific to multi-part
  (text+media) messages distinct from the +8 seen for pure-text prompts, that
  overhead is folded into these derived counts rather than isolated separately.
- Reference instruction token counts (`llama-tokenize --no-bos`) confirmed exact
  match to protocol: vision instruction = **65**, audio instruction = **28**.

## Deviations from protocol (all explicit)

1. **Cyrillic path broke the native toolchain twice.** The working directory
   (`OneDrive\Рабочий стол\qolda-avl-gguf`) contains Cyrillic characters. This broke
   (a) MSVC/nvcc's CUDA compiler-ID build step (`CMakeCUDACompilerId.cu`: "cannot
   open source file", path garbled to `???????\????` in the vcxproj), and separately
   (b) `llama-tokenize -f <path>`'s `fopen()` on the same path ("failed to open
   file"). Neither is a patch or model defect — it's an OS/toolchain Unicode-path
   bug. **Fix:** relocated the entire working set (llama.cpp source, build output,
   downloaded models, benchmark inputs) to an ASCII-only path, `C:\qolda-bench\`,
   and ran everything from there. The build itself and all benchmark I/O in this
   report are unaffected by this bug once relocated.
2. **CUDA toolkit version mismatch.** The system has both CUDA v12.6 and v13.1
   installed. Default `cmake -B build -DGGML_CUDA=ON` (Visual Studio generator)
   silently selected v13.1's `nvcc`, and `CMAKE_CUDA_ARCHITECTURES=native` detection
   failed ("No CUDA devices found") despite `nvidia-smi` clearly seeing the GPU —
   most likely because driver 572.16 doesn't support the CUDA 13.1 runtime used by
   that detection probe. **Fix:** pinned the build to the 12.6 toolset explicitly
   (`-T cuda=12.6`) and set `-DCMAKE_CUDA_ARCHITECTURES=89` (Ada Lovelace, RTX 4090)
   directly. Confirmed via configure log: `CUDA compiler identification is NVIDIA
   12.6.20`, `CMAKE_CUDA_ARCHITECTURES_NATIVE=89-real`.
3. **HF Hub "Xet" download backend hung indefinitely (0 bytes progress) twice.**
   This repo is served through HF's newer Xet storage backend
   (`xet-bridge-us` redirect). `hf download` stalled at a fixed byte offset with the
   download process still alive but making zero progress for 5+ minutes, on two
   separate attempts (including a plain resume). **Fix:** set
   `HF_HUB_DISABLE_XET=1` to force the classic HTTP/Range-request download path,
   which completed all remaining files without further stalls.
4. **One file was silently corrupted during transfer, caught before use.** After
   the Xet-disabled download completed, a full sha256 cross-check against HF's
   authoritative `lfs.sha256` (queried live via the HF API, not the protocol's
   fixed hashes — those cover only the 4 shared benchmark artifacts, not the model
   weights) found `Q6_K/Qolda-AVL-5B-Q6_K.gguf` had the **correct byte size but
   wrong content** (hash `f21b6ccc514d...` vs authoritative
   `d392af001feea486200a19e016414529e86a4ad2d0b696012dee3950b21b5ca5`). Re-downloaded
   and re-verified; final hash matches. All 7 model files' sha256 (see below) were
   cross-checked against the HF API before any benchmark run.
5. **Operator error: an `rm -rf` ran in the same batch as an unverified `cp -r`,
   losing 3 files temporarily.** When relocating the downloaded models off the
   Cyrillic OneDrive path, a directory copy (`cp -r`) silently left 3 files at 0
   bytes and 1 file truncated (OneDrive "Files On-Demand" placeholder files that
   hadn't hydrated locally at copy time). The verification (`find`) and the
   deletion of the OneDrive source (`rm -rf`) were dispatched in the same parallel
   tool-call batch instead of sequentially, so the source was deleted before the
   copy was confirmed good. Caught immediately on the next check (file sizes were
   still visibly wrong) and fixed by re-downloading the 4 affected files directly
   into the ASCII-path destination (bypassing OneDrive entirely) — no data was
   permanently lost since these are public, freely re-downloadable model weights,
   not user data, but this cost time and should not have happened; sequencing
   destructive operations after verification, not alongside it, is the standing
   rule this violated.
6. **Windows power plan was "Balanced," not "Best Performance," at the start.**
   Only "Balanced" was exposed by `powercfg -list` (ASUS laptops commonly hide the
   stock Windows performance plans in favor of Armoury Crate). Unhid and activated
   "High performance" via `powercfg -duplicatescheme 8c5e7fda-e8bf-4a96-9a85-
   a6e23a8c635c` + `powercfg -setactive <guid>` before any measured run (confirmed
   via `powercfg -getactivescheme`). **Armoury Crate's specific profile
   (Silent/Performance/Turbo/Manual) could not be verified or set via CLI/registry**
   — no supported command-line surface was found, and undocumented registry edits
   were judged too risky to attempt on a benchmark run. If the paper requires a
   specific Armoury Crate mode, please confirm/set it manually; this was not done
   or verified for this run.
7. **No HWiNFO64 or LibreHardwareMonitor installed.** Only GPU package power
   (`nvidia-smi --query-gpu=power.draw`) was logged. **CPU package power was not
   captured — total laptop wall power is higher than the `avg_power_w` /
   `energy_j_per_1k_tok` figures reported in `results.csv`.**
8. **`--parallel 1` was set explicitly** (llama-server defaults to 4 parallel
   slots), to guarantee true single-stream/batch=1 behavior and to keep the
   KV-cache accounting in Finding §1 correct (4 slots would reserve ~4× the KV
   budget even with only 1 request in flight).
9. **`--no-mmap` was not passed.** Not applicable here: `-ngl 999` fully offloads
   every layer to VRAM for every variant (confirmed — no partial-offload rows in
   the CSV), so no weights sit resident in system RAM during inference; mmap's
   default (on) only affects the initial file-load path from disk.
10. Audio input worked through the standard `/v1/chat/completions` `input_audio`
    content block on every request — the `llama-mtmd-cli` fallback path was never
    needed.

## Environment

- OS: Windows 11 Home Single Language, build 10.0.26200 (64-bit)
- CPU: Intel(R) Core(TM) Ultra 9 185H
- GPU: NVIDIA GeForce RTX 4090 Laptop GPU, 16376 MiB VRAM, driver 572.16
- RAM: 33,736,028,160 bytes (≈31.4 GiB)
- CUDA toolkit used for build: 12.6.20 (v13.1 also present on system but not used —
  see Deviation #2)
- MSVC: Visual Studio 2022 Community, toolset 14.38.33130 (cl.exe 19.38.33143.0)
- CMake: 4.1.1
- Power source: AC (laptop plugged in)
- Windows power plan: High performance (corrected from Balanced — Deviation #6)
- Armoury Crate: running, specific performance profile not verified (Deviation #6)
- GPU idle baseline: 46°C / ~9.3 W (initial check) → measured idle power
  11.14 W before the run, 12.24 W after (60 s baseline each, `nvidia-smi
  power.draw`)
- GPU temperature per variant (start → end of each variant's measured cells,
  after the 180 s thermal soak): BF16 54→73°C, Q8_0 68→73°C, Q6_K 69→73°C,
  Q5_K_M 69→72°C, Q4_K_M 69→73°C. No indication of thermal throttling at these
  temperatures.

## Artifact hashes (first 12 chars of sha256)

Fixed shared artifacts (verified against the protocol's stated hashes — exact match):

| file | sha256 (first 12) |
|---|---|
| bench_image.jpg | d45840444cde |
| prompts_text.txt | bb5c5cf05481 |
| bench_audio_30s.wav | 94c91da69169* |
| bench_audio_10s.wav | c00cefb4f2d1 |

`*` protocol listed `94c91da6916aa32b9ba6cd5e602a7eb941c3b2b637f46a1744dff7a8602bbbc7` — first 12 chars `94c91da69169`, matches exactly.

Model files (verified against HF API's authoritative `lfs.sha256`, not the
protocol's list — that only covers the 4 files above):

| file | size (GiB) | sha256 (first 12) |
|---|---|---|
| BF16/Qolda-AVL-5B-BF16.gguf | 7.498 | 7df60f9052bd |
| Q8_0/Qolda-AVL-5B-Q8_0.gguf | 3.986 | 613406fad8ab |
| Q6_K/Qolda-AVL-5B-Q6_K.gguf | 3.079 | d392af001fee |
| Q5_K_M/Qolda-AVL-5B-Q5_K_M.gguf | 2.691 | 193793b63208 |
| Q4_K_M/Qolda-AVL-5B-Q4_K_M.gguf | 2.326 | 4846476c27ae |
| mmproj/mmproj-Qolda-AVL-5B-F16.gguf | 2.043 | 041aa58d1d39 |
| mmproj/mmproj-Qolda-AVL-5B-vision-only-F16.gguf | 0.779 | c06b37209e45 |

llama.cpp commit: `ea63b4d32ea1b66bdbe369be7f9443f6c00f8b31` (2026-07-30,
"vulkan: Support quantized concat (#25684)"). Patch (`qwen3avl-support.patch`,
sha256 `bb27de1efd5b...`) applied cleanly with `git apply` — zero conflicts, one
new file (`conversion/qwen3avl.py`), 7 files modified.

## Exact commands run

```bash
# clone + pin + patch
git clone https://github.com/ggml-org/llama.cpp llama.cpp
cd llama.cpp
git checkout ea63b4d
git apply ../models/llama.cpp-patch/qwen3avl-support.patch

# build (relocated to C:\qolda-bench\llama.cpp — see Deviation #1)
cmake -B build -G "Visual Studio 17 2022" -T cuda=12.6 -DGGML_CUDA=ON \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=89
cmake --build build -j --config Release \
  --target llama-server llama-mtmd-cli llama-tokenize

# model download (Xet disabled — see Deviation #3)
export HF_HUB_DISABLE_XET=1
hf download issai/Qolda-AVL-5B-GGUF \
  BF16/Qolda-AVL-5B-BF16.gguf Q8_0/Qolda-AVL-5B-Q8_0.gguf \
  Q6_K/Qolda-AVL-5B-Q6_K.gguf Q5_K_M/Qolda-AVL-5B-Q5_K_M.gguf \
  Q4_K_M/Qolda-AVL-5B-Q4_K_M.gguf \
  mmproj/mmproj-Qolda-AVL-5B-F16.gguf \
  mmproj/mmproj-Qolda-AVL-5B-vision-only-F16.gguf \
  --local-dir models

# power plan
powercfg -duplicatescheme 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
powercfg -setactive fa079c95-1f81-45db-b272-0ab8f6883009

# server (per variant; example Q4_K_M primary)
llama-server.exe -m models/Q4_K_M/Qolda-AVL-5B-Q4_K_M.gguf \
  --mmproj models/mmproj/mmproj-Qolda-AVL-5B-F16.gguf \
  -ngl 999 -c 4096 --parallel 1 --host 127.0.0.1 --port 8080

# benchmark harness (full matrix: 5 variants x 6 modes x 5 reps
# + 2 control rows x 5 reps = 160 measured requests, 3 discarded warmups
# per server session, 180s thermal soak per variant)
python3 bench.py
```

`bench.py` (in this directory) is the complete harness: parses `prompts_text.txt`
per the marker rules, builds OpenAI-compatible `/v1/chat/completions` requests
(text string content for text modes; `image_url`/`input_audio` content blocks for
vision/audio), streams the response, computes `ttft_ms` from first content-bearing
SSE chunk, `decode_tps`/`prefill_tps` from the server's own `timings` object in the
final chunk, and samples `nvidia-smi` VRAM+power and the server process's RSS
(via `psutil`, including child processes) at 200 ms throughout each request window.
