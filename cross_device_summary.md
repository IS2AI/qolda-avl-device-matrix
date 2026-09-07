# Qolda-AVL-5B-GGUF — cross-device deployment benchmark

Three devices, one shared protocol, measured independently. This document reconciles
the three result sets, states what can and cannot be compared, and reports the
findings that survive reconciliation.

**Every figure here traces to a row in a device `results.csv` or to a file in that
device's working folder. Nothing is interpolated, estimated, or averaged across
devices. Where a number is missing it is written as missing.**

These are speed measurements. No output quality was evaluated on any device; the
model card supplies perplexity, KLD and top-1 agreement per quantization.

---

## 1. Devices

| | Device 1 | Device 2 | Device 3 |
|---|---|---|---|
| `device_class` | `discrete-gpu-laptop` | `unified-memory-laptop` | `flagship-smartphone` |
| Machine | ASUS ROG, RTX 4090 Laptop GPU | MacBook Pro `Mac16,7`, M4 Pro | OnePlus 13R `CPH2691` |
| Backend | CUDA 12.6, driver 572.16 | Metal 4 | CPU, ARM NEON + i8mm |
| Memory | 16.0 GiB VRAM (+31.4 GiB host) | 24 GB unified | 14.85 GiB RAM + 9.50 GiB zram |
| Toolchain | MSVC 14.38, CUDA 12.6.20 | Apple clang 17.0.0, CLT only (no full Xcode, SDK 15.5) | Android NDK r29, clang 21.0.0 |
| Power state | AC, High performance plan | AC, High Power Mode (`pmset powermode 2`) | **unplugged**, screen off, airplane mode + WiFi |
| Rows | 160 | 160 | 151 |

Device 2 ran without full Xcode. Metal still built — llama.cpp compiles shader
pipelines at runtime. Report its toolchain as "CLT only, SDK 15.5"; there is no Xcode
version for this device.

---

## 2. Verification — what was checked, and how

### 2.1 Schema

All three CSVs carry the protocol's 26 columns **in identical order**, verified by
direct comparison against the protocol list:

```
device_class, device_name, backend, llamacpp_commit, patch_applied, variant,
mmproj_variant, mode, prompt_tokens, image_tokens, audio_tokens, audio_seconds,
gen_tokens, run_idx, thermal_state, ttft_ms, encoder_ms, prefill_tps, decode_tps,
total_ms, peak_rss_gb, peak_vram_gb, avg_power_w, idle_power_w,
energy_j_per_1k_tok, notes
```

Device 3 appends two further columns **after** these 26: `avg_power_w_raw` and
`power_samples_used`. The leading schema is byte-compatible and the three files
concatenate positionally. **No column or ordering mismatch exists.**

### 2.2 Commit and patch

`llamacpp_commit` is `ea63b4d32ea1b66bdbe369be7f9443f6c00f8b31` on all 471 rows,
with no other value present on any device. `patch_applied` is `yes` on all 471 rows.
All three summaries report `qwen3avl-support.patch` applied cleanly with zero
conflicts. The patch file present in Device 2's and Device 3's folders hashes to
`bb27de1efd5b546d74b834395570f49d5e017db872f0586a771edf59d0f89bf3`, matching all
three summaries. Device 3 additionally reports the on-device build string
`version: 10198 (ea63b4d32)`.

### 2.3 Fixed artifacts

Recomputed directly from the files in Device 2's and Device 3's working folders:

| file | sha256 | D1 | D2 | D3 |
|---|---|---|---|---|
| `bench_image.jpg` | `d45840444cdef3c8d81eaa73c720f78e49fd3274c510fc49fc12665c43bb2330` | attested | **recomputed, match** | **recomputed, match** |
| `prompts_text.txt` | `bb5c5cf054819d5775533e5fb8d2914196865351b1c5144fe7bdee35759dcc09` | attested | **recomputed, match** | **recomputed, match** |
| `bench_audio_30s.wav` | `94c91da6916aa32b9ba6cd5e602a7eb941c3b2b637f46a1744dff7a8602bbbc7` | attested | **recomputed, match** | **recomputed, match** |
| `bench_audio_10s.wav` | `c00cefb4f2d1c942f02eedebbc21dee4ccbc90cd1b2e08a40f18f162cfa77d0c` | attested | **recomputed, match** | **recomputed, match** |

Device 1's working folder is not on this machine, so its four hashes could not be
recomputed here. Its `summary.md` records an exact match, and the operator confirms
having verified Device 1's artifacts, models and protocol file directly. Recorded as
operator-verified.

### 2.4 Generation settings — verified in source on all three devices

| device | source | settings |
|---|---|---|
| D1 | `bench.py:27-28`, `:124-126`, `:144-145` | `n_predict=256, temperature=0.7, top_p=0.95, top_k=20, seed=1234, ignore_eos=True, cache_prompt=False`, `-c 4096`, `--parallel 1` |
| D2 | `bench_lib.py:162-163` | identical `GEN` dict |
| D3 | `bench_lib.py:436-437` | identical `GEN` dict |

The three settings blocks are the same. `gen_tokens = 256` on all 471 rows, which is
what `n_predict=256` with `ignore_eos=true` produces and what a natural stop would
not. **State the use of `ignore_eos` in the paper**: throughput windows are identical
by construction, which matters because the base model is Qwen3-VL-4B-**Thinking** and
would otherwise emit variable-length reasoning before its answer.

### 2.5 The two fixed Kazakh instructions — byte-identical on all three devices

Extracted from source and hashed:

| instruction | sha256 | length | D1 | D2 | D3 |
|---|---|---|---|---|---|
| vision | `f63fa7539ec1d197b8f363edda67d19ce4fbb0fd037152dab32bafdd2d466b26` | 108 chars | match | match | match |
| audio | `ff56a068450c55a4a96e7a25f6c6c97e5a30e9f4efc606f40e5062264fcbe9a8` | 39 chars | match | match | match |

```
Суреттегі нысандарды, олардың өзара орналасуын, түстері мен көрінетін жазуларды егжей-тегжейлі сипаттап бер.
Аудиодағы сөйлеуді сөзбе-сөз жазып шық.
```

### 2.6 Memory units — all three are GiB

The most likely source of a wrong cross-device comparison, checked in code rather
than assumed:

| device | column | computation | unit |
|---|---|---|---|
| D1 | `peak_vram_gb` | `max(vram_mib) / 1024` (`bench.py:242`) | **GiB** |
| D1 | `peak_rss_gb` | `rss / 1024**3` (`bench.py:223`) | **GiB** |
| D2 | `peak_rss_gb` | `peak_kb * 1024 / GIB`, `GIB = 1024**3` (`bench.py:141`) | **GiB** |
| D3 | `peak_rss_gb` | `peak_hwm_kb * 1024 / B.GIB`, `GIB = 1024**3` (`bench.py:298`) | **GiB** |

**No unit conversion is required anywhere.** Note that Device 3's `summary.md` prose
writes "GB" in several places where the column is GiB; the column is authoritative.

### 2.7 Token counts

`prompt_tokens` for the three multimodal modes is **identical on all three devices**:
vision 1101, audio-30s 1540, audio-10s 540. Devices 2 and 3 independently decompose
these as instruction + media + a fixed 12-token chat-template overhead, pinned from
the vision row (`1101 = 1024 + 65 + 12`) and confirmed on both audio rows. Device 3's
`token_census.json` records the rule explicitly:

```json
"chat_template_overhead_tokens": 12,
"derivation": "image/audio tokens = server prompt_n - instruction tokens - 12 template tokens"
```

Device 1 subtracted the instruction but **not** the 12 template tokens, so its derived
columns read 1036 / 1512 / 512 against 1024 / 1500 / 500 on the other two. This is a
bookkeeping difference in a derived column. The underlying prompt is identical on all
three devices and the encode workload was the same. **Devices 2 and 3 land exactly on
the protocol's ~1500 / ~500 prediction, at 50.0 audio tokens per second of audio for
both clips.**

---

## 3. Measurement boundaries — read before any performance table

Four things differ by device in ways that make specific columns non-comparable. They
are stated here once and referenced by every table below.

| | Device 1 (CUDA) | Device 2 (Metal) | Device 3 (ARM CPU) |
|---|---|---|---|
| **Power boundary** | **GPU package only** (`nvidia-smi power.draw`). CPU package **not captured** — no HWiNFO64 or LibreHardwareMonitor installed. Total wall power is higher than reported. | **SoC package** (`powermetrics`, `CPU Power` + `GPU Power`). Excludes display and DRAM rails; excludes ANE. | **Whole-device battery draw**. `/sys/class/power_supply/battery/*` unreadable under Android 16 SELinux; `cmd battery get -f current_now` × `dumpsys battery voltage`, in **mA × mV**. |
| `idle_power_w` | 11.139 W (single value) | 0.600 W (single value) | 0.4587 / 0.5002 / 0.4737 W (three locations) |
| **Memory column** | `peak_vram_gb` (`peak_rss_gb` is host-side only, ~2.79 GiB, not the model footprint) | `peak_rss_gb`; `peak_vram_gb` is the literal string `unified (no discrete VRAM)` | `peak_rss_gb`; same literal string in `peak_vram_gb` |
| **Text endpoint** | `/v1/chat/completions` → `prompt_tokens` 138 / 523 / 2058 | `/completion` → 128 / 513 / 2048 | `/completion` → 128 / 513 / 2048 |
| **Transport** | localhost | localhost | **WiFi, phone unplugged.** Direct TCP, not `adb forward`. |
| `encoder_ms` | blank, all 160 rows | blank, all 160 rows | blank, all 151 rows |
| `--reasoning-format none` | **not set** | set | set |
| mmap | **on** | off (every row notes `mmap=off`) | off |
| Multimodal content order | `[text instruction, media]` | `[media, text instruction]` | `[media, text instruction]` |
| Performance profile | High performance plan; **Armoury Crate profile unverified** | High Power Mode — **non-default**, raises sustained clocks and fan speed | stock, bare device, no cooling |

Three consequences that must not be lost:

1. **`avg_power_w` and `energy_j_per_1k_tok` measure three different quantities.**
   They never appear in one column in this document.
2. **`peak_vram_gb` cannot be coerced to a number on Devices 2 and 3.** It is a
   string. Unified memory has one figure and it lives in `peak_rss_gb`.
3. **Device 1's text `prefill_tps` and `ttft_ms` have a different denominator.** It
   prefilled 10 more tokens per text row: +7.8 % on `text-128`, +2.0 % on `text-512`,
   +0.5 % on `text-2048`.

---

## 4. Metric selection — what is tabulated together, and why

| metric | comparable across all three? | decision |
|---|---|---|
| `decode_tps` | **Yes** | One table, all devices, all modes. Decode is unaffected by the endpoint difference (the 10-token offset changes starting context, not the decode loop) and Device 3's client/server ratio is **0.996 median across all 151 rows** (min 0.936; 3 rows below 0.95, flagged `TRANSPORT-AFFECTED`). |
| `prefill_tps`, `ttft_ms` — **multimodal** | **Yes** | One table. `prompt_tokens` is identical (1101 / 1540 / 540) on all three devices, so the denominator matches. |
| `prefill_tps`, `ttft_ms` — **text** | **No** | Separate table. Device 1's denominator is 138 / 523 / 2058 against 128 / 513 / 2048. Re-running is not possible without the Windows machine. |
| peak memory | **Partly** | One table, but Device 1 reports VRAM and Devices 2 and 3 report unified RSS. Different quantities, same unit. Device 3's figure is invalid for ranking under swap (see §7.5). |
| `avg_power_w`, `energy_j_per_1k_tok` | **No** | Three separate blocks, each labelled with its boundary. |
| `encoder_ms` | **No data on any device** | Blank on all 471 rows. Isolated analytically in §6.1. |

---

## 5. Cross-device performance tables

Three significant figures. Median of 5 reps unless the `n` column says otherwise.
All rows are `mmproj_variant = audio+vision`, `thermal_state = sustained`.
Device 3 rows are the `-t 6` configuration (see §8.3).

### 5.1 decode_tps — median (min–max)

| variant | mode | D1 CUDA | D2 Metal | D3 ARM CPU |
|---|---|---|---|---|
| BF16 | text-128 | 49.0 (48.8–49.2) | 28.5 (28.3–28.6) | 1.16 (1.14–1.17) |
| BF16 | text-512 | 49.1 (48.6–49.6) | 28.4 (28.4–28.4) | 1.13 (1.11–1.15) **n=2** |
| BF16 | text-2048 | 48.0 (47.7–48.4) | 27.6 (27.4–27.6) | N/A (not measured: battery floor; BF16 prefill 1.42 tok/s ⇒ ~20–25 min/run) |
| BF16 | vision | 48.8 (47.8–49.2) | 28.1 (27.8–28.1) | N/A (same reason) |
| BF16 | audio-30s | 48.3 (48.0–48.9) | 27.9 (27.8–27.9) | N/A (same reason) |
| BF16 | audio-10s | 48.7 (48.4–49.6) | 28.4 (28.2–28.4) | N/A (same reason) |
| Q8_0 | text-128 | 70.7 (67.6–73.5) | 50.4 (50.4–50.4) | 7.59 (7.33–7.82) |
| Q8_0 | text-512 | 72.2 (69.6–73.0) | 49.8 (49.4–49.8) | 6.63 (5.91–6.74) |
| Q8_0 | text-2048 | 69.1 (67.2–69.8) | 47.4 (46.7–47.5) | 4.52 (4.37–4.70) |
| Q8_0 | vision | 69.0 (68.9–72.4) | 48.9 (48.8–48.9) | 5.87 (5.59–5.92) |
| Q8_0 | audio-30s | 69.2 (66.8–70.4) | 48.2 (48.1–48.2) | 5.28 (5.17–5.42) |
| Q8_0 | audio-10s | 70.2 (69.3–71.8) | 49.7 (48.9–49.7) | 6.82 (6.65–6.91) |
| Q6_K | text-128 | 80.2 (80.0–82.1) | 61.3 (60.8–61.4) | 6.92 (6.75–6.99) |
| Q6_K | text-512 | 79.5 (77.4–80.5) | 60.5 (60.4–60.5) | 6.20 (6.15–6.21) |
| Q6_K | text-2048 | 75.3 (74.1–76.5) | 57.0 (56.9–57.0) | 4.45 (4.41–4.49) |
| Q6_K | vision | 77.6 (73.8–79.0) | 59.1 (59.0–59.1) | 5.36 (5.35–5.40) |
| Q6_K | audio-30s | 75.4 (74.6–79.6) | 58.2 (58.2–58.2) | 4.88 (4.82–4.92) |
| Q6_K | audio-10s | 77.6 (75.2–79.7) | 60.3 (59.4–60.4) | 6.13 (6.04–6.30) |
| Q5_K_M | text-128 | 84.3 (81.8–85.3) | 60.6 (60.1–60.7) | 8.51 (8.21–8.57) |
| Q5_K_M | text-512 | 86.8 (80.8–88.6) | 59.8 (59.8–60.0) | 7.31 (6.95–7.48) |
| Q5_K_M | text-2048 | 82.4 (81.4–84.3) | 56.3 (56.2–56.3) | 4.81 (4.77–4.84) |
| Q5_K_M | vision | 82.0 (80.3–84.8) | 55.5 (55.4–55.5) | 5.84 (5.82–5.94) |
| Q5_K_M | audio-30s | 83.1 (75.1–84.4) | 58.1 (57.9–58.4) | 5.34 (5.29–5.38) |
| Q5_K_M | audio-10s | 86.4 (85.9–87.5) | 60.0 (59.3–60.1) | 6.90 (6.43–6.93) |
| Q4_K_M | text-128 | 91.4 (90.3–94.5) | 75.8 (75.7–75.8) | 9.78 (9.69–10.7) |
| Q4_K_M | text-512 | 93.9 (90.6–94.6) | 74.2 (74.2–74.3) | 8.90 (8.19–8.97) |
| Q4_K_M | text-2048 | 89.5 (86.0–90.8) | 68.7 (68.7–68.7) | 5.27 (5.20–5.33) |
| Q4_K_M | vision | 88.9 (81.9–91.9) | 72.3 (72.3–72.4) | 6.68 (6.42–6.72) |
| Q4_K_M | audio-30s | 89.0 (88.1–92.2) | 70.7 (70.6–70.8) | 5.85 (5.84–5.94) |
| Q4_K_M | audio-10s | 90.8 (89.9–93.6) | 74.2 (74.1–74.2) | 8.14 (8.08–8.24) |

Device 1's within-cell spread is materially wider than Device 2's (up to 11.2 % on
Q5_K_M audio-30s against ≤1.7 % anywhere on Device 2). Device 2 is the most
reproducible of the three.

### 5.2 TTFT and prefill — multimodal only (comparable denominators)

`prompt_tokens` = 1101 / 1540 / 540 on all three devices.
Device 1 shows `all-5 median [runs 2–5 median]` because `run_idx=1` of every
vision and audio cell is a cold-start outlier (§7.6).

| variant | mode | D1 ttft_ms | D2 ttft_ms | D3 ttft_ms | D1 pf | D2 pf | D3 pf |
|---|---|---|---|---|---|---|---|
| BF16 | vision | 1360 [1320] | 2160 | N/A (not measured: battery floor) | 1170 | 514 | N/A |
| BF16 | audio-30s | 1820 [1780] | 2350 | N/A (same) | 1780 | 666 | N/A |
| BF16 | audio-10s | 1250 [1230] | 1150 | N/A (same) | 1120 | 484 | N/A |
| Q8_0 | vision | 1320 [1290] | 2200 | 155000 | 1250 | 505 | 7.21 |
| Q8_0 | audio-30s | 1860 [1810] | 2410 | 124000 | 1690 | 650 | 12.6 |
| Q8_0 | audio-10s | 1290 [1290] | 1160 | 99800 | 1100 | 476 | 5.47 |
| Q6_K | vision | 1280 [1280] | 2290 | 170000 | 1280 | 485 | 6.50 |
| Q6_K | audio-30s | 2000 [1910] | 2530 | 163000 | 1600 | 618 | 9.70 |
| Q6_K | audio-10s | 1320 [1310] | 1210 | 118000 | 1070 | 455 | 4.67 |
| Q5_K_M | vision | 1430 [1410] | 2360 | 167000 | 1200 | 470 | 6.60 |
| Q5_K_M | audio-30s | 1800 [1790] | 2640 | 143000 | 1750 | 593 | 10.8 |
| Q5_K_M | audio-10s | 1120 [1110] | 1250 | 106000 | 1270 | 442 | 5.12 |
| Q4_K_M | vision | 1370 [1330] | 2260 | 161000 | 1230 | 491 | 6.88 |
| Q4_K_M | audio-30s | 1850 [1840] | 2500 | 135000 | 1690 | 627 | 11.6 |
| Q4_K_M | audio-10s | 1250 [1220] | 1200 | 102000 | 1140 | 462 | 5.29 |

`pf` = `prefill_tps`. Device 3's `ttft_ms` carries residual WiFi transport overhead
of roughly 1–2 % at these magnitudes; `prefill_tps` does not.

### 5.3 TTFT and prefill — text modes, NOT directly comparable

**Device 1 prefilled a different number of tokens.** Reported separately for that
reason. The offset is stated per mode; it is not corrected, because correcting it
would require re-measurement.

| variant | mode | D1 (`prompt_n`=138/523/2058) | D2 (128/513/2048) | D3 (128/513/2048) |
|---|---|---|---|---|
| | | ttft_ms / prefill_tps | ttft_ms / prefill_tps | ttft_ms / prefill_tps |
| BF16 | text-128 | 249 / 1140 | 155 / 833 | 90500 / 1.42 |
| BF16 | text-512 | 314 / 3040 | 611 / 842 | 366000 / 1.42 **n=2** |
| BF16 | text-2048 | 644 / 4150 | 2460 / 833 | N/A (not measured: battery floor) |
| Q8_0 | text-128 | 255 / 1060 | 157 / 825 | 2040 / 65.3 |
| Q8_0 | text-512 | 374 / 2680 | 615 / 837 | 9300 / 55.9 |
| Q8_0 | text-2048 | 629 / 4200 | 2530 / 809 | 51800 / 41.4 |
| Q6_K | text-128 | 214 / 1360 | 166 / 781 | 4010 / 32.1 |
| Q6_K | text-512 | 378 / 2400 | 648 / 795 | 16700 / 30.8 |
| Q6_K | text-2048 | 676 / 3840 | 2680 / 765 | 77600 / 26.4 |
| Q5_K_M | text-128 | 264 / 1230 | 176 / 737 | 3650 / 35.8 |
| Q5_K_M | text-512 | 349 / 2640 | 685 / 751 | 15000 / 34.4 |
| Q5_K_M | text-2048 | 650 / 4060 | 2830 / 725 | 72300 / 28.4 |
| Q4_K_M | text-128 | 243 / 1300 | 163 / 793 | 2930 / 44.2 |
| Q4_K_M | text-512 | 376 / 2580 | 635 / 811 | 11600 / 44.2 |
| Q4_K_M | text-2048 | 646 / 4020 | 2640 / 776 | 59700 / 34.3 |

Device 1's text `prefill_tps` also rises steeply with prompt length (1060–1360 at
128 tokens to 3840–4200 at 2048), which is the signature of a fixed per-request
overhead dominating the short-prompt measurement rather than a real throughput
difference. Device 2's is flat (725–842 across the whole range), so Device 2's
prefill figure is the more reliable characterisation of steady-state prefill rate.

### 5.4 Peak memory (GiB) — different quantities, same unit

**D1 = `peak_vram_gb` (discrete VRAM). D2, D3 = `peak_rss_gb` (unified resident).**
Do not read across the row as if it were one quantity.

| variant | mode | D1 VRAM | D2 unified RSS | D3 unified RSS |
|---|---|---|---|---|
| BF16 | text-512 | 12.3 | 10.3 | 7.77 ⚠ |
| BF16 | audio-10s | 12.5 | 10.7 | N/A (not measured: battery floor) |
| Q8_0 | text-512 | 8.79 | 7.70 | 6.80 ⚠ |
| Q8_0 | text-2048 | 8.78 | 7.70 | 4.96 ⚠ |
| Q8_0 | audio-10s | 8.96 | 8.52 | 7.92 ⚠ |
| Q6_K | text-512 | 7.86 | 6.63 | 6.18 |
| Q6_K | audio-10s | 8.04 | 7.77 | 6.50 |
| Q5_K_M | text-512 | 7.47 | 6.24 | 5.49 |
| Q5_K_M | audio-10s | 7.65 | 7.39 | 6.83 |
| Q4_K_M | text-512 | 7.11 | 5.32 | 5.28 |
| Q4_K_M | text-2048 | 7.11 | 5.33 | 5.26 |
| Q4_K_M | vision | 7.25 | 5.95 | 5.93 |
| Q4_K_M | audio-30s | 7.29 | 6.25 | 6.36 |
| Q4_K_M | audio-10s | 7.29 | 6.52 | 6.53 |

⚠ = `SWAP-AFFECTED`. **Device 3's Q8_0 and BF16 figures understate the true
requirement** because evicted pages are not resident. Q8_0 `text-2048` at 4.96 GiB
against `text-512` at 6.80 GiB is the clearest example: memory pressure rose and the
measured number *fell*. See §7.5.

Device 3's Q4_K_M column tracks Device 2's closely — the largest gap across the six
modes is 0.17 GiB (`text-128`, 5.49 against 5.32) and four of six are within 0.07 GiB.
That is the expected result for two unified-memory devices running the same weights
at the one quantization where neither swaps, and is a useful check that both
instrumented memory the same way.

### 5.5 Power and energy — three separate boundaries, never one column

**Device 1 — GPU package only. CPU package not captured. Idle 11.139 W.**

| variant | text-512 | text-2048 | vision | audio-30s | audio-10s |
|---|---|---|---|---|---|
| BF16 | 110 W / 1980 J | 110 W / 2070 J | 103 W / 1910 J | 102 W / 1860 J | 103 W / 1840 J |
| Q8_0 | 107 W / 1330 J | 108 W / 1400 J | 100 W / 1270 J | 94.5 W / 1200 J | 96.3 W / 1210 J |
| Q6_K | 103 W / 1160 J | 106 W / 1260 J | 96.1 W / 1110 J | 92.3 W / 1050 J | 94.0 W / 1060 J |
| Q5_K_M | 106 W / 1100 J | 105 W / 1120 J | 95.2 W / 1010 J | 91.0 W / 948 J | 92.9 W / 942 J |
| Q4_K_M | 102 W / 994 J | 103 W / 1040 J | 96.5 W / 925 J | 89.9 W / 882 J | 90.9 W / 874 J |

**Device 2 — SoC package (CPU + GPU). Excludes display, DRAM, ANE. Idle 0.600 W.**

| variant | text-512 | text-2048 | vision | audio-30s | audio-10s |
|---|---|---|---|---|---|
| BF16 | 19.3 W / 658 J | 22.2 W / 780 J | 21.5 W / 742 J | 21.6 W / 750 J | 20.2 W / 686 J |
| Q8_0 | 23.8 W / 464 J | 26.2 W / 536 J | 25.8 W / 514 J | 26.1 W / 527 J | 24.5 W / 479 J |
| Q6_K | 25.3 W / 407 J | 28.3 W / 484 J | 27.5 W / 453 J | 27.9 W / 468 J | 26.0 W / 421 J |
| Q5_K_M | 28.7 W / 468 J | 30.7 W / 532 J | 29.9 W / 527 J | 30.5 W / 510 J | 29.2 W / 475 J |
| Q4_K_M | 25.1 W / 328 J | 28.9 W / 410 J | 28.1 W / 379 J | 28.2 W / 389 J | 26.5 W / 348 J |

**Device 3 — whole-device battery draw, unplugged. Idle 0.459 / 0.474 / 0.500 W by
location.**

| variant | text-512 | text-2048 | vision | audio-30s | audio-10s |
|---|---|---|---|---|---|
| BF16 | 3.53 W / 2680 J **n=2** | N/A (not measured) | N/A | N/A | N/A |
| Q8_0 | 7.60 W / 1050 J | 6.46 W / 1300 J | 4.58 W / 696 J | 4.89 W / 834 J | 4.79 W / 621 J |
| Q6_K | 7.33 W / 1110 J | 6.65 W / 1380 J | 4.95 W / 836 J | 4.93 W / 902 J | 4.72 W / 684 J |
| Q5_K_M | 7.15 W / 922 J | 6.19 W / 1190 J | 4.59 W / 706 J | 4.95 W / 841 J | 4.73 W / 616 J |
| Q4_K_M | 7.33 W / 765 J | 6.04 W / 1050 J | 4.38 W / 589 J | 4.58 W / 696 J | 4.34 W / 475 J |

15 Device 3 rows carry `UNRELIABLE POWER` (fewer than 8 usable samples), mostly short
text rows. Every Device 3 row also carries `avg_power_w_raw`, the uncorrected mean;
the median correction is **+0.24 W** (range −0.12 to +1.78 W).

**One cross-device power statement is safe**, because Device 3's boundary is a strict
superset of Device 1's: the phone's **whole-device** draw under load, 4.34–7.82 W, is
below the laptop GPU's **package-only** draw of 89.9–110 W by more than an order of
magnitude. The inequality holds in that direction regardless of what Device 1's
uncaptured CPU package would add. No such statement can be made between Devices 1
and 2, or between 2 and 3.

### 5.6 Control cells (Q4_K_M, n=5 each) — projector cost

| device | a+v `text-512` | `none` `text-512` | projector cost | a+v `vision` | `vision-only` `vision` | audio branch |
|---|---|---|---|---|---|---|
| D1 (VRAM) | 7.106 | 4.549 | **2.557 GiB** | 7.246 | 5.785 | **1.461 GiB** |
| D2 (RSS) | 5.320 | 3.600 | **1.720 GiB** | 5.950 | 4.810 | **1.140 GiB** |
| D3 (RSS) | 5.280 | 3.330 | **1.950 GiB** | 5.930 | 4.640 | **1.290 GiB** |

Reference: the audio+vision projector is 2.043 GiB on disk; the vision-only projector
is 0.779 GiB; the difference is 1.264 GiB.

Throughput is unchanged by the projector on all three devices: D1 93.9 vs 93.9 tok/s,
D2 74.2 vs 74.5, D3 8.90 vs 8.36 (Device 3's 6 % gap is within its thermal variation
and its own summary attributes it to thermal state, not to the projector).

---

## 6. Synthesis

### 6.1 The padded-window audio property holds on all three backends, but it is only *visible* on CPU

`encoder_ms` is blank on all 471 rows, on all three devices, for the same reason:
`llama-server` reports no separate encode latency. To compare like with like, the
encoder was isolated the same way on every device — subtract the LLM prefill cost at
that variant's own measured text prefill rate:

`encoder ≈ prompt_n / prefill_tps(mode) − prompt_n / prefill_tps(text-512)`

| device | variant | encoder(10 s) | encoder(30 s) | ratio 10/30 | vision encoder | TTFT ratio 30 s / 10 s |
|---|---|---|---|---|---|---|
| D1 CUDA | Q8_0 | 0.290 s | 0.339 s | 0.854 | 0.469 s | 1.44 |
| D1 CUDA | Q4_K_M | 0.262 s | 0.312 s | 0.841 | 0.471 s | 1.48 |
| D2 Metal | Q8_0 | 0.489 s | 0.529 s | 0.924 | 0.865 s | 2.08 |
| D2 Metal | Q4_K_M | 0.503 s | 0.557 s | 0.903 | 0.885 s | 2.08 |
| D3 ARM CPU | Q8_0 | 89.1 s | 94.7 s | 0.941 | 133 s | 1.24 |
| D3 ARM CPU | Q4_K_M | 89.9 s | 97.9 s | 0.918 | 135 s | 1.32 |

Full ranges across all variants with data: D1 0.747–0.877, D2 0.903–0.981,
D3 0.902–0.941.

**The property replicates on every backend.** Three times the audio content costs
between 1.02× and 1.34× the encoder time on all three devices. Device 2's analytic
figures are independently validated: its direct `llama-mtmd-cli` measurement gives
458 ms for the 10 s clip and 460 ms for the 30 s clip, against 0.50 s and 0.56 s
derived here from server timings alone.

**What differs by backend is how much this matters.** The encoder is a fixed cost;
what changes is its share of TTFT.

| device | encoder share of audio-30s TTFT (Q4_K_M) | consequence |
|---|---|---|
| D1 CUDA | 0.312 s of 1.85 s ≈ **17 %** | Halving audio length nearly halves TTFT. The padded window is close to invisible. |
| D2 Metal | 0.557 s of 2.50 s ≈ **22 %** | TTFT scales almost linearly with audio tokens (ratio 2.08). The padded window is present but not dominant. |
| D3 ARM CPU | 97.9 s of 135 s ≈ **73 %** | Audio length barely affects TTFT (ratio 1.32). **A 10-second utterance costs ~90 s before the first token.** |

The deployment consequence is specific to CPU inference and it is severe. On the
phone, sending shorter audio does not buy responsiveness, and chunking audio makes
things worse — every chunk pays the full padded-window encoder cost. On both GPU
backends the LLM prefill dominates, so shorter audio does help, and chunking is
merely inefficient rather than prohibitive.

*Note on precision:* Device 1's analytic encoder figures are the least reliable of
the three, because on that device the encoder is a small fraction of a TTFT that also
contains base64 upload and CUDA graph-initialisation overhead, and its text
`prefill_tps` reference is itself unstable across prompt lengths (§5.3). The
direction of the finding is solid on Device 1; the absolute 0.26–0.31 s should be
read as an upper-bounded estimate, not a measurement.

### 6.2 The Q6_K > Q5_K_M inversion is Metal-specific

Device 2 observed Q6_K decoding faster than Q5_K_M in all six modes despite being the
larger file. Tested on all three devices:

| mode | D1 CUDA | D2 Metal | D3 ARM CPU |
|---|---|---|---|
| text-128 | −4.84 % | **+1.16 %** | −18.7 % |
| text-512 | −8.34 % | **+1.17 %** | −15.2 % |
| text-2048 | −8.61 % | **+1.24 %** | −7.48 % |
| vision | −5.42 % | **+6.49 %** | −8.22 % |
| audio-30s | −9.29 % | +0.17 % | −8.61 % |
| audio-10s | −10.2 % | **+0.50 %** | −11.2 % |

(Q6_K decode relative to Q5_K_M. Positive = Q6_K faster.)

**The inversion appears only on Metal.** On CUDA and on ARM CPU, Q6_K is slower than
Q5_K_M in all six modes, and on ARM CPU by a wide margin.

Confidence: Device 2's within-cell spread is 0.00–1.66 %, so its four largest margins
(text ×3 and vision) are outside noise; the two audio margins (+0.17 %, +0.50 %) are
within it and should be read as "no worse", not "faster". Device 3's margins of
7.5–18.7 % are far outside its 0.93–7.25 % spread and are unambiguous. Device 1's
margins of 4.8–10.2 % sit against a wider spread of 1.86–11.2 %, so individual cells
are borderline, but the direction is consistent in all six modes, which is itself
evidence.

Practical reading: Q5_K_M is the worse choice on Metal (larger latency, lower
throughput, only 0.39 GiB saved). On the other two backends Q6_K is dominated —
Device 3's summary states it is dominated on every axis it measured there.

### 6.3 Quantization is non-monotonic on ARM CPU only

Device 3's F6 finding — that Q8_0 outperforms the intermediate K-quants on prefill —
does not appear on either GPU backend.

Prefill_tps at `text-512`, ordered by weight size:

| variant | weights | D1 CUDA | D2 Metal | D3 ARM CPU |
|---|---|---|---|---|
| BF16 | 7.498 GiB | 3040 | 842 | 1.42 |
| Q8_0 | 3.986 GiB | 2680 | 837 | **55.9** |
| Q6_K | 3.079 GiB | 2400 | 795 | 30.8 |
| Q5_K_M | 2.691 GiB | 2640 | 751 | 34.4 |
| Q4_K_M | 2.326 GiB | 2580 | 811 | 44.2 |

On Device 3, Q8_0 prefills **1.81× faster than Q6_K** and **1.26× faster than
Q4_K_M**, despite being the largest quantized variant. Device 3's summary attributes
this to `i8mm` integer matrix-multiply consuming 8-bit weights directly while
K-quants require per-sub-block unpacking; the build has `HAVE_MATMUL_INT8` enabled.
Because TTFT on that device is prefill-dominated for every multimodal mode, this
lands on the metric users feel: **Q8_0 has the lowest audio-30s TTFT of any variant
on the phone (124 s, against Q4_K_M's 135 s and Q6_K's 163 s)** — the opposite of the
usual "smaller quant is faster" expectation.

Neither GPU backend shows this. Device 2's prefill is flat within 11 % across the
whole range. Device 1's is noisy for the reason in §5.3 and shows no consistent
ordering.

### 6.4 Quantization scaling against what weight size alone predicts

BF16 → Q4_K_M is a 3.22× reduction in weight bytes (7.498 → 2.326 GiB). Measured
`text-512` decode speedup and memory reduction:

| device | decode BF16 → Q4_K_M | speedup | vs 3.22× predicted | peak memory ratio |
|---|---|---|---|---|
| D1 CUDA | 49.1 → 93.9 tok/s | **1.91×** | far below | 12.3 → 7.11 GiB (0.58×) |
| D2 Metal | 28.4 → 74.2 tok/s | **2.61×** | below | 10.3 → 5.32 GiB (0.52×) |
| D3 ARM CPU | 1.13 → 8.90 tok/s | **7.88×** | far above | 7.77 → 5.28 GiB (0.68×) ⚠ |

Three different regimes:

- **CUDA** returns least. At 1.91× against a 3.22× weight reduction, decode on the
  4090 is not purely weight-bandwidth-bound; fixed per-token cost dominates.
- **Metal** returns more (2.61×) but still under-delivers against weight size.
- **ARM CPU** returns far *more* than weight size predicts, and this is an artifact,
  not a quantization property. BF16 on the phone runs permanently swapped — 7.67 GB
  resident plus 4.18 GB in zram, with 1.10 GB `MemAvailable` remaining. The 7.88× is
  measuring the cost of escaping swap, not the cost of the extra weight bytes. Its
  memory ratio (0.68×) is likewise unreliable, since the BF16 baseline is a
  swap-suppressed figure.

Memory scaling is closer to prediction than throughput scaling on all three devices,
because the constant terms (projector, KV cache, compute buffers) do not shrink with
quantization. Those constants are quantified next.

### 6.5 The fixed-overhead finding replicates, but the KV cache figure is disputed

Device 1's Finding §1 reports a fixed VRAM overhead constant across quantization.
Recomputed here from its CSV:

| variant | weights | measured peak VRAM | overhead if KV = 0.352 GiB | overhead if KV = 0.563 GiB |
|---|---|---|---|---|
| BF16 | 7.498 | 12.473 | 2.580 | 2.369 |
| Q8_0 | 3.986 | 8.957 | 2.576 | 2.365 |
| Q6_K | 3.079 | 8.041 | 2.567 | 2.356 |
| Q5_K_M | 2.691 | 7.654 | 2.568 | 2.357 |
| Q4_K_M | 2.326 | 7.289 | 2.568 | 2.357 |

(overhead = measured − weights − mmproj 2.043 GiB − KV, `audio-30s` rows)

**The constancy is robust** — the spread is 13 MiB across a weight range spanning
2.3 to 7.5 GiB, under either KV assumption. Deployment planning should budget a fixed
figure on top of weights + projector + KV, not a quant-scaled one.

**The magnitude depends on an unresolved conflict between Devices 1 and 2.**

| device | derivation | head_dim | KV @ 4096 ctx |
|---|---|---|---|
| D1 | `embedding_length / head_count` = 2560 / 32 | 80 | 0.352 GiB (360 MiB) |
| D2 | explicit `head_dim` from GGUF metadata | 128 | 0.563 GiB (576 MiB) |

Both cannot be right. The arithmetic is unambiguous: `2 × 36 layers × 8 KV heads ×
head_dim × 4096 ctx × 2 bytes` gives 360 MiB at head_dim 80 and exactly 576 MiB at
head_dim 128. Device 2 reports runtime confirmation of the 576 MiB figure
(`llama_kv_cache: MTL0 KV buffer size = 576.00 MiB`) and the protocol's own estimate
was ~0.6 GB, which matches 0.563 GiB and not 0.352 GiB.

Deriving `head_dim` as `embedding_length / head_count` is invalid for Qwen3-family
architectures, which carry an explicit `head_dim` that is not that quotient. On the
evidence available, **Device 2's 0.563 GiB is the correct figure and Device 1's
2.57 GiB fixed overhead should be restated as ~2.36 GiB.** This is flagged rather
than silently corrected: the line Device 2 quotes is not present in its delivered
server logs, which begin after model-load geometry, so the runtime confirmation is
attestation rather than something reproducible from the files here.

### 6.6 The audio projector runs on the accelerator on both GPU backends

The headline risk for Device 2 was a CPU fallback in the audio path, which would have
made its audio TTFT structurally incomparable to the CUDA device. It did not happen.
Device 2 reports `clip_ctx: CLIP using MTL0 backend` with `projector: qwen3avl` for
audio and `qwen3vl_merger` for vision, no per-op fallback warnings, and compute
buffers of 183 MiB MTL0 against 1.46 MiB CPU for audio (the CPU side being
mel-spectrogram input prep, which is CPU-side by design) and 356 MiB against 24.9 MiB
for vision.

Device 1 reports the audio path working through the standard `input_audio` content
block on every request. Device 3 is a CPU-only build by construction, so the question
does not arise there.

**No device used the `llama-mtmd-cli` fallback path for any measured row.** The string
`mtmd` appears zero times in all three `results.csv` files. Device 2 used
`llama-mtmd-cli` separately to measure encoder latency and deliberately kept those
numbers out of its CSV so the two sources are never mixed within a mode.

### 6.7 Feasibility boundaries

| device | capacity | largest variant that runs | first that fails | boundary evidence |
|---|---|---|---|---|
| D1 CUDA | 16.0 GiB VRAM | **BF16**, peak 12.5 GiB | none — all five fit, 160/160 rows, zero failures | 3.5 GiB headroom at BF16 |
| D2 Metal | 24 GB unified | **BF16**, peak 10.7 GiB | none — all five fit, 160/160 rows, zero failures, zero N/A cells | Predicted totals matched measured peaks to within 0.5–1.0 GB |
| D3 ARM CPU | 14.85 GiB RAM + 9.50 GiB zram | **Q4_K_M** is the only variant that runs resident | **Q8_0 swaps** (~4.7 GB to zram, `MemAvailable` fell to 2.70 GB); **BF16 runs permanently swapped** and is unusable | 7.67 GB resident + 4.18 GB zram, 1.10 GB `MemAvailable` remaining |

The interesting boundary is Device 3's, and it is not an OOM. **BF16 did not fail and
was not refused.** It loaded in 26.1 s and completed every run attempted, at
1.16 tok/s decode and 90.5 s TTFT on a 128-token prompt — 8.4× slower decode and 32×
slower prefill than Q4_K_M. Prefill is pinned at 1.42 tok/s regardless of prompt
length, which is the signature of a memory-bandwidth-bound rather than compute-bound
workload, and the process stayed in state `R` rather than `D`, so this is a stable
swap-bound equilibrium rather than live thrashing. That is why its numbers are
reproducible to within 3 %.

This is the measured deployment envelope, and it is more informative than a refusal
would have been: **on a 16 GB flagship phone the model runs at every quantization and
is usable at exactly one.**

### 6.8 Thermal — Device 3 only, and the sustained figures are the conservative ones

Devices 1 and 2 are `thermal_state = sustained` on all 320 rows, both after a
3-minute soak per variant. Neither collected cold measurements, so no cross-device
throttling comparison is possible.

Device 3 zone temperatures across the whole session, parsed from the per-run
`tz_start` / `tz_end` fields (302 readings):

| zone | range |
|---|---|
| `cpu-1-2-0` (big core) | 28.1 – 85.6 °C |
| `cpuss-0` (CPU subsystem) | 26.3 – 84.0 °C |
| `skin-msm-therm` | 25.2 – 65.8 °C |
| `shell_back` (chassis skin) | 23.7 – 52.5 °C |

Residual drift within each cell, measured as the change in `decode_tps` from
`run_idx` 1 to `run_idx` 5 across all 25 Device 3 cells with 5 reps: **median
−0.60 %**, with 16 of 25 cells negative. The two largest declines (Q8_0 `text-512`
−10.1 %, Q4_K_M `text-512` −7.35 %) are both in cells that also carry
`SWAP-AFFECTED`, so memory pressure rather than temperature is the more likely cause.
A −0.60 % median across five reps is small relative to the 0.93–7.25 % within-cell
spread and supports Device 3's own conclusion that the device reaches a stable
sawtooth (48 → 76 °C per run, recovering in the 16–20 s gap) rather than
progressively throttling.

**Frame the Device 3 numbers as conservative.** They are sustained-load figures taken
after warm-up, which is what a deployment claim should rest on. Burst figures would
be higher and would overstate real-world performance. The one caveat is scope: this
is *duty-cycled* sustained load with 16–20 s recovery gaps, and the 20-minute
continuous decay curve that would have covered genuinely uninterrupted generation was
never run.

---

## 7. Limits of this comparison

Every caveat that survives into the tables above.

### 7.1 Energy is not comparable across devices

Three boundaries: GPU package (D1), SoC package (D2), whole-device battery (D3).
Device 1 does not capture CPU package power at all, so its laptop's true wall draw is
higher than any figure it reports. Device 2 excludes display and DRAM rails. Device 3
includes everything the battery feeds. **`avg_power_w` and `energy_j_per_1k_tok` are
reported in three separate blocks in §5.5 and must never be merged into one column.**
The single safe cross-device statement is the superset inequality in §5.5.

### 7.2 Device 1's text prefill and TTFT have a different denominator

138 / 523 / 2058 tokens against 128 / 513 / 2048 on the other two, because Device 1
sent text through `/v1/chat/completions` while Devices 2 and 3 used `/completion`.
Verified in source on all three. The text latency table (§5.3) is separated for this
reason and the offset is stated per mode. Decode throughput is unaffected.

### 7.3 Device 1 ran a non-comparable server configuration in two further respects

It did not set `--reasoning-format none`, which both other devices set to stop the
Thinking checkpoint routing `<think>` output into a separate `reasoning_content`
field. Its harness computes TTFT from the first content-bearing SSE chunk, which may
handle it, but the configuration differs. It also ran with mmap **on** while both
other devices ran `mmap=off`; under `-ngl 999` this affects only the load path, but
the configurations are not identical.

### 7.4 Device 2 ran a non-default performance profile

macOS High Power Mode (`pmset powermode 2`), raising sustained clocks and fan speed,
retained by explicit operator decision. Low Power Mode was disabled as the protocol
required, so this is compliant as written. **Device 2's throughput and power are
best-case.** Device 1's Armoury Crate profile could not be read or set from the
command line and is unverified, so neither laptop is a matched control for the other.

### 7.5 Device 3's `peak_rss_gb` cannot rank memory across variants

Under zram pressure, evicted pages are not resident, so peak RSS moves the wrong way.
Q8_0 `text-2048` reads 4.96 GiB against `text-512`'s 6.80 GiB — lower under higher
pressure. Naively read, Q8_0 would look lighter than Q6_K. Affected rows carry
`swap_used=X->Y GB` and `SWAP-AFFECTED`; 42 Device 3 rows and 3 Device 2 rows are
flagged. Swap tracking was added partway through Device 3's Q8_0 block, so its three
text modes lack the field — an instrumentation gap, not a measurement, and not
backfilled. Device 3's memory figures are marked ⚠ in §5.4 wherever this applies.

### 7.6 Device 1's vision and audio TTFT medians run high

`run_idx=1` of every Device 1 vision cell is 2.1–2.5× the median of runs 2–5, with a
smaller 1.3–1.7× elevation on both audio modes. Cause: the protocol's three warm-up
requests used only the `text-128` prompt, so the first vision or audio request in
each server session paid one-time CUDA kernel and graph initialisation for that
modality. The outliers are retained per protocol. §5.2 therefore reports both the
all-5 median and the runs-2–5 median for Device 1; the difference is 0–90 ms.
Devices 2 and 3 do not report this pattern.

### 7.7 Device 3 had a network in the measurement path

Phone unplugged over WiFi, per protocol. `decode_tps` and `ttft_ms` are defined
client-side, so transport is included. After the fixes (direct TCP rather than
`adb forward`; a host-side ICMP keepalive to defeat WiFi power-save), the
client/server decode ratio across all 151 rows is **median 0.996, min 0.936, with 3
rows below 0.95** flagged `TRANSPORT-AFFECTED`. `decode_tps` and `prefill_tps` are
trustworthy. **`ttft_ms` and `total_ms` retain residual transport overhead** — about
1–2 % on audio and vision rows where TTFT is 100–160 s, proportionally larger on
`text-128` where TTFT is ~3 s. Cross-device latency claims in this document rest on
`prefill_tps` wherever possible.

### 7.8 Device 3's power method is a forced substitution

`/sys/class/power_supply/battery/*` returns Permission denied under Android 16 /
OxygenOS 16, and `dumpsys powerstats` lists no EnergyConsumers, so there are no ODPM
rails. Current comes from `cmd battery get -f current_now` and voltage from
`dumpsys battery`, in **mA × mV**, not the protocol's assumed µA × µV — µA × µV gives
0.0000004 W, six orders of magnitude low, while mA × mV gives 0.406 W, inside the
protocol's 0.3–0.8 W sanity band. 15 rows have fewer than 8 usable power samples and
carry `UNRELIABLE POWER`.

`idle_power_w` differs across three measurement locations (0.4587 / 0.5002 /
0.4737 W). Idle *current* was stable (119 / 114 / 118.7 mA); the spread is battery
voltage against state of charge (3.866 / 4.389 / 3.991 V). Per-row energy uses the
baseline in force when that row was measured, and `raw_runs.jsonl` retains every raw
current and voltage sample, so energy is recomputable against an SoC-matched baseline
if the paper needs that precision.

**Device 3's `summary.md` is stale on this point.** It states `idle_power_w = 0.433 W`
and says that is the value in `results.csv`. It is not — the CSV carries 0.459 (84
rows), 0.474 (42 rows) and 0.500 (25 rows). `env.json` explains why and marks 0.433 W
`idle_superseded`: it was measured with Doze **enabled**, while all runs execute with
Doze disabled. **`env.json` is authoritative; do not quote 0.433 W.**

### 7.9 `encoder_ms` is empty on every row of every device

All 471 rows. `llama-server` reports no separate encode latency at any usable
verbosity on this build. §6.1 isolates the encoder analytically using the same method
on all three devices so the comparison is method-matched. Device 2 additionally has a
direct `llama-mtmd-cli` measurement (458 ms / 460 ms / 836 ms vision), deliberately
kept out of its CSV; it is used in §6.1 only to validate the analytic method, never
mixed into a table with server-derived figures.

### 7.10 Incomplete cells on Device 3

- **BF16**: `text-128` (n=5) and `text-512` (n=2) only. The other four modes were not
  measured. Not a failure — BF16 runs, but prefills at 1.42 tok/s, so a single vision
  or audio run would take 20–25 minutes and the block was stopped at the battery
  floor. Marked `N/A (not measured: battery floor; BF16 prefill 1.42 tok/s ⇒ ~20–25
  min/run)` throughout, never a bare N/A. **These four cells are absent from
  `results.csv` entirely** — the reason exists only in `summary.md` prose, so a naive
  merge drops them silently.
- **cold**: 4 rows only (`text-512` n=3, `vision` n=1). The operator cut the cold
  block for time after 4 of 9 planned runs; `audio-30s` cold was never run. A partial
  sample, labelled as such. No throttling ratio is computed from it here.
- **The 20-minute thermal decay curve was never run.** `thermal_decay.csv` does not
  exist. A reviewer asking what happens under genuinely continuous generation with no
  recovery gaps is not answered by this dataset.

### 7.11 Device 1's artifacts could not be re-verified here

Its working folder is not on this machine; only `results.csv`, `summary.md` and
`bench.py` are present. Its four artifact hashes, its model file hashes and its
tokenizer readings are attestation from its summary plus the operator's direct
confirmation. Devices 2 and 3 were re-verified from the files.

Related: Device 1's summary reports that `llama-tokenize --no-bos` on the patched
`ea63b4d` build yields 130 / 515 / 2050 for the three prompt bodies, a consistent +2
against the reference. Devices 2 and 3 both ran the same tool on the same commit
against the same hash-verified `prompts_text.txt` and both got 128 / 513 / 2048.
Tokenisation is CPU-side and backend-independent, so this cannot be a CUDA / Metal /
ARM effect. Two devices agree; the third is unreconciled and could not be reproduced
here. The CSV values are unaffected either way — Device 1's server-reported
`prompt_tokens` is 138 / 523 / 2058 regardless.

### 7.12 Device 3's thread-sensitivity rows share a cell with the baseline

`Q4_K_M / audio+vision / text-512 / sustained` contains **15 rows, not 5**: three
server configurations (`-t 4`, `-t 6`, `-t 8`) distinguished only by a `threads=`
token inside `notes`. Grouping on variant × mmproj × mode × thermal_state alone
medians all 15 and returns 6.49 tok/s, which is the `-t 4` figure. **All Device 3
numbers in this document are the `-t 6` baseline (8.90 tok/s at that cell).** The
`-t 4` and `-t 8` rows are real measurements and are retained in the source CSV; they
are excluded from the primary tables because they vary a parameter other than
variant × mode. Device 3's own finding stands: `-t 8` is 42.7 % slower than `-t 6`,
worse than `-t 4`, because the two little A520 cores are stragglers at every barrier.

### 7.13 Recording gaps

- **Ambient temperature was recorded at Device 3's location 1 only (23 °C).** It was
  **not measured** at locations 2 or 3. Device 3's thermal claims rest on per-run
  on-device zone temperatures, which are recorded for every row and are unaffected by
  this gap.
- **Device 2's screen brightness was never recorded numerically** (macOS 26 exposes
  no readable percentage without full Xcode). It was held fixed for the whole session
  and the display rail sits outside Device 2's SoC-package power boundary, so it
  cannot affect any reported number. Omitted.
- **The optional battery repeat set was not run on Device 2.** There is no
  `sustained (battery)` data for that device.

### 7.14 Discrepancies between the handoff notes and the delivered data

Recorded so the paper does not repeat them:

| claim in handoff notes | what the data shows |
|---|---|
| Device 3 deviations run D1–D18 | `summary.md` contains **D1–D15**. There is no D16, D17 or D18. |
| Padded-window ratio 0.897–0.932 across four variants | Recomputed from the CSV: **0.902–0.941** (Q4_K_M 0.918, Q5_K_M 0.918, Q6_K 0.902, Q8_0 0.941). The finding replicates; the stated range does not reproduce. |
| Device 3 vision encoder 134.3–135.4 s | Recomputed: **133.0–135.1 s** across the same four variants. |
| Device 3 `idle_power_w` = 0.433 W in `results.csv` | The CSV carries 0.459 / 0.474 / 0.500 W. See §7.8. |

One divergence appears in no summary: **Device 1 orders multimodal content as
`[text instruction, media]` while Devices 2 and 3 both order it `[media, text
instruction]`.** Token counts are unaffected (1101 / 1540 / 540 on all three), but the
prompts are not byte-identical in sequence.

---

## 8. What could not be compared

| item | why |
|---|---|
| `energy_j_per_1k_tok` across devices | Three different power boundaries (§7.1) |
| `avg_power_w` across devices | Same, except the superset inequality in §5.5 |
| Text `ttft_ms` and `prefill_tps` between D1 and the others | Different prompt token counts (§7.2) |
| `encoder_ms` from the CSV on any device | Blank on all 471 rows (§7.9) |
| Peak memory between D1 and D2/D3 as one quantity | VRAM against unified RSS (§3) |
| Memory ranking across variants on D3 | Invalid under swap (§7.5) |
| Cold vs sustained throttling on any device | D1 and D2 collected no cold rows; D3's cold sample is 4 rows (§7.10) |
| Continuous-load thermal behaviour on D3 | The decay curve was never run (§7.10) |
| BF16 multimodal on D3 | Not measured, battery floor (§7.10) |
| D1's artifact and model hashes | Working folder not on this machine (§7.11) |
| Any output quality metric | Not evaluated on any device by design; see the model card |

---

## 9. Sources

| device | path | files used |
|---|---|---|
| D1 | `~/ISSAI/results/rtx/` | `results.csv` (160 rows), `summary.md`, `bench.py` |
| D2 | `~/ISSAI/qolda-avl-gguf/` | `results.csv` (160), `summary.md`, `bench.py`, `bench_lib.py`, `env.json`, `file_manifest.json`, `idle_baselines.json`, `idle_clean.json`, `logs/`, the four fixed artifacts |
| D3 | `~/ISSAI/qolda-avl-gguf-one-plus/` | `results.csv` (151), `summary.md`, `bench.py`, `bench_lib.py`, `env.json`, `token_census.json`, the four fixed artifacts |

`~/ISSAI/results/{rtx,macbook,one-plus}/` hold byte-identical copies of the nine
delivered files, verified by sha256 against the working folders.
