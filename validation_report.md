# Cross-device validation report — Qolda-AVL-5B-GGUF three-device benchmark

Scope: `rtx/`, `macbook/`, `one-plus/` as delivered. Every statement below traces to
a row in a device CSV, a line in a device `bench.py`, or a quoted line in a device
`summary.md`. Nothing is estimated.

**VERDICT: PHASE 1 FAILS. Checks 5, 6 and 7 diverge. Merging is not performed.**

---

## Phase 0 — inventory

### Files found

| path | bytes | rows (CSV, excl. header) | device |
|---|---|---|---|
| `rtx/bench.py` | 17,675 | — | Windows / RTX 4090 Mobile / CUDA |
| `rtx/results.csv` | 39,242 | 160 | Windows / RTX 4090 Mobile / CUDA |
| `rtx/summary.md` | 21,480 | — | Windows / RTX 4090 Mobile / CUDA |
| `macbook/bench.py` | 11,392 | — | MacBook Pro / M4 Pro / Metal |
| `macbook/results.csv` | 62,050 | 160 | MacBook Pro / M4 Pro / Metal |
| `macbook/summary.md` | 24,515 | — | MacBook Pro / M4 Pro / Metal |
| `one-plus/bench.py` | 27,207 | — | OnePlus 13R / SD 8 Gen 3 / CPU arm64 |
| `one-plus/results.csv` | 106,879 | 151 | OnePlus 13R / SD 8 Gen 3 / CPU arm64 |
| `one-plus/summary.md` | 39,213 | — | OnePlus 13R / SD 8 Gen 3 / CPU arm64 |
| `source_kk.txt` | 351,641 | — | shared (not device-specific) |

Attribution is unambiguous. Each CSV carries a single `device_class` /
`device_name` / `backend` triple:

- `rtx` → `discrete-gpu-laptop` / `RTX 4090 Laptop GPU (ASUS ROG, 16GB VRAM)` / `CUDA`
- `macbook` → `unified-memory-laptop` / `MacBook Pro / Apple M4 Pro 14-core / 24 GB unified` / `Metal`
- `one-plus` → `flagship-smartphone` / `OnePlus 13R (CPH2691) / Snapdragon 8 Gen 3 SM8650 / 16 GB LPDDR5X` / `CPU (ARM NEON/i8mm)`

All three devices contributed all three required files. No file is unattributable.

`source_kk.txt` (194,184 characters, 25,461 whitespace-separated words, 1,453 lines,
Kazakh Wikipedia prose on Қазақстан) is a shared input, not a device deliverable. It
is required for the Phase 4 fertility computation.

### Files referenced by the summaries but NOT delivered

These are not required deliverables, but several validation items below could
otherwise have been checked directly against them rather than against prose.

| file | referenced by | what it would have settled |
|---|---|---|
| `bench_lib.py` | `macbook/bench.py:4`, `one-plus/bench.py:18` | generation settings, prompt bodies, and the two Kazakh instruction strings on 2 of 3 devices (check 3, check 4) |
| `raw_runs.jsonl` | macbook, one-plus summaries | per-run server `timings`, raw power samples, full thermal zone sets |
| `thermal_decay.csv` | one-plus summary header | never produced; the decay run was not executed (see D6 / OP-6) |
| `env.json` | one-plus summary | power calibration, battery level range |
| `power_calc.py` | `one-plus/bench.py:19` | the Android power correction itself |
| `aggregate.py`, `parse_prompts.py` | macbook summary | median computation, prompt parsing |
| `artifact_provenance.md` | macbook summary (dev. 14) | how the fixed artifacts were generated |

### Row counts

160 + 160 + 151 = **471 rows**. `gen_tokens = 256` on all 471. `run_idx` is 1–5 on
all three devices. No row is duplicated.

---

## Phase 1 — identity checks

| # | item | verdict |
|---|---|---|
| 1 | `llamacpp_commit` = `ea63b4d`, patch applied everywhere | **PASS** |
| 2 | Four artifact hashes match | **PASS** (see note) |
| 3 | Generation settings identical | **PASS** on available evidence; direct code verification **MISSING** on 2 devices |
| 4 | Two Kazakh instructions byte-identical | **PASS** for audio (byte-verified); **PARTIAL** for vision |
| 5 | `prompt_tokens` = 128 / 513 / 2048 on every device | **FAIL** |
| 6 | `image_tokens` identical on every device | **FAIL** |
| 7 | `audio_tokens` identical on every device | **FAIL** |
| 8 | `mmproj_variant` = `audio+vision` primary + 2 Q4_K_M controls per device | **PASS** |

---

### 1. Commit and patch — PASS

`llamacpp_commit` is `ea63b4d32ea1b66bdbe369be7f9443f6c00f8b31` on all 471 rows, with
no other value present. `patch_applied` is `yes` on all 471 rows.

All three summaries name the same patch and the same patch hash:
`qwen3avl-support.patch`, sha256 `bb27de1efd5b…`. All three report it applied cleanly
with zero conflicts. Mac and OnePlus enumerate the same 8 changed files
(`conversion/__init__.py`, `conversion/qwen3avl.py` (new), `gguf-py/gguf/constants.py`,
`tools/mtmd/clip-graph.h`, `tools/mtmd/clip-impl.h`, `tools/mtmd/clip.cpp`,
`tools/mtmd/models/whisper-enc.cpp`, `tools/mtmd/mtmd.cpp`); RTX reports "one new
file, 7 files modified", which is the same set. OnePlus additionally reports the
on-device `--version` string `version: 10198 (ea63b4d32)`.

### 2. Artifact hashes — PASS, with an attestation gap on one device

| file | expected sha256 | rtx | macbook | one-plus |
|---|---|---|---|---|
| `bench_image.jpg` | `d45840444cdef3c8d81eaa73c720f78e49fd3274c510fc49fc12665c43bb2330` | first 12 only | full match | full match |
| `prompts_text.txt` | `bb5c5cf054819d5775533e5fb8d2914196865351b1c5144fe7bdee35759dcc09` | first 12 only | full match | full match |
| `bench_audio_30s.wav` | `94c91da6916aa32b9ba6cd5e602a7eb941c3b2b637f46a1744dff7a8602bbbc7` | full match | full match | full match |
| `bench_audio_10s.wav` | `c00cefb4f2d1c942f02eedebbc21dee4ccbc90cd1b2e08a40f18f162cfa77d0c` | first 12 only | full match | full match |

RTX's summary records only the first 12 hex characters for three of the four files,
while stating that the comparison against the full protocol hashes was an exact match.
The 12 recorded characters match. This is an attestation gap, not a divergence. The
artifacts themselves are not in the delivered folder, so no hash can be recomputed
here.

### 3. Generation settings — PASS on available evidence, code MISSING on two devices

Verifiable in source on RTX only (`rtx/bench.py:27-28`, `:124-126`, `:144-145`):

```
N_PREDICT = 256
GEN_KW = dict(temperature=0.7, top_p=0.95, top_k=20, seed=1234,
              ignore_eos=True, cache_prompt=False)
N_CTX = 4096
... "n_predict": N_PREDICT, "stream": True, **GEN_KW
... "-c", str(self.n_ctx), "--parallel", "1"
```

All nine required settings match.

`macbook/bench.py` and `one-plus/bench.py` both delegate request construction to
`B.build_body(...)` in `bench_lib.py`, which was not delivered. Their settings are
attested only in prose:

- macbook summary: "`n_predict = 256`, `ignore_eos = true`, `temperature = 0.7`,
  `top_p = 0.95`, `top_k = 20`, `seed = 1234`, `n_ctx = 4096`, batch size 1 (single
  stream), `cache_prompt = false`".
- one-plus summary: "`n_predict=256`, `ignore_eos=true`, `temperature=0.7`,
  `top_p=0.95`, `top_k=20`, `seed=1234`, `n_ctx=4096`, `cache_prompt=false`, single
  stream".

Both statements are exact matches to the required set. Independent corroboration from
the data: `gen_tokens = 256` on all 471 rows across all three devices, which is what
`n_predict=256` with `ignore_eos=true` produces and what a natural stop would not.

Recorded as PASS. The missing `bench_lib.py` is flagged so a reviewer knows the
Mac and Android settings rest on prose plus the `gen_tokens` invariant, not on code.

### 4. Kazakh instructions — PASS for audio, PARTIAL for vision

Audio instruction. The literal string appears in `rtx/bench.py:45` and in the
`llama-mtmd-cli` smoke-test command quoted verbatim in both other summaries. All
three are byte-identical (sha256 of the UTF-8 string, first 16 hex:
`ff56a068450c55a4`):

```
Аудиодағы сөйлеуді сөзбе-сөз жазып шық.
```

Vision instruction. Present verbatim only in `rtx/bench.py:44`:

```
Суреттегі нысандарды, олардың өзара орналасуын, түстері мен көрінетін жазуларды егжей-тегжейлі сипаттап бер.
```

The Mac and Android summaries do not quote it and `bench_lib.py` is absent, so no
byte comparison is possible. Indirect evidence that it is the same string: all three
devices independently report the vision instruction tokenising to exactly **65**
tokens and the audio instruction to exactly **28** tokens under the patched `ea63b4d`
tokenizer, and all three record `prompt_tokens = 1101` for `vision`. Byte identity is
consistent with the data but not directly verified on two devices.

### 5. `prompt_tokens` for the three text modes — FAIL

Actual values recorded in the CSVs:

| mode | rtx | macbook | one-plus | required |
|---|---|---|---|---|
| `text-128` | **138** | 128 | 128 | 128 |
| `text-512` | **523** | 513 | 513 | 513 |
| `text-2048` | **2058** | 2048 | 2048 | 2048 |

Mac and Android agree exactly with the required values on all three modes, in every
row. RTX is +10 on all three modes, in every row.

**Cause, identified in the code.** `rtx/bench.py:122-126` sends text prompts as a
`messages` array to `/v1/chat/completions`, so the server applies the qwen3vl chat
template and `prompt_n` includes the wrapper. The Mac summary records the opposite
choice explicitly as its deviation 3: "Text modes used the raw `/completion`
endpoint … Text was sent as the bare prompt body (as instructed) so that `prompt_n`
is directly comparable to 128/513/2048 without chat-template padding. Had text gone
through the chat endpoint, `prompt_n` would have read ~140/525/2060." The Android
device matches the Mac.

**Consequence.** This is not a bookkeeping difference. RTX prefilled 10 more tokens
than the other two devices on every text row: 7.8 % more work on `text-128`, 2.0 % on
`text-512`, 0.5 % on `text-2048`. `ttft_ms` and `prefill_tps` for the RTX text modes
are therefore not directly comparable to the other two devices at face value, and the
error is largest on the shortest prompt, which is the one most sensitive to it.

**A second, unresolved conflict sits inside this check.** RTX's summary §3 reports
that `llama-tokenize --no-bos` on the patched `ea63b4d` build gives 130 / 515 / 2050
for the three prompt bodies, a consistent +2 against the reference, "verified 3
independent ways (`-p`, `-f`, `--stdin`)", and attributes it to a real
tokenizer-version difference. The Android summary reports running
`llama-tokenize --no-bos` **on-device with the same patched `ea63b4d` build** and
getting 128 / 513 / 2048. The Mac summary reports the same, 128 / 513 / 2048, and
calls the cross-check passed. Same commit, same patch, same `prompts_text.txt`
(hash verified identical on all three devices).

Two devices against one. RTX's +2 cannot be a hardware or backend effect, since
tokenisation is CPU-side and architecture-independent. It looks like a measurement
error on the RTX side (a stray leading or trailing byte in the file handed to
`llama-tokenize`, most plausibly, given deviation 1 on that device concerns
`llama-tokenize -f` failing on a Unicode path and needing the file relocated). It is
flagged here rather than resolved by picking a side. Note that the +2 claim is
independent of the +10 in the CSV: 130 + 8 template = 138, which is what the CSV
holds. If the raw body is in fact 128, the RTX template overhead is +10 rather
than +8, and either way the CSV value is 138.

**The tokenizer cross-check that was left pending is answered as follows:** two of
three devices, tokenising the same file under the same patched commit, return exactly
128 / 513 / 2048. The third returns 130 / 515 / 2050 and is unreconciled.

### 6. `image_tokens` — FAIL

| device | `image_tokens` for `bench_image.jpg` | `prompt_tokens` (vision) |
|---|---|---|
| rtx | **1036** | 1101 |
| macbook | **1024** | 1101 |
| one-plus | **1024** | 1101 |

The underlying measurement is identical: `prompt_tokens = 1101` on all three devices,
on all 15 vision rows each. The divergence is entirely in how the derived column was
computed:

- RTX: `1101 − 65 (instruction) = 1036`.
- Mac and Android: `1101 − 65 (instruction) − 12 (chat template) = 1024`.

The Mac summary pins the 12-token template overhead from the vision row itself
(`1101 = 1024 + 65 + 12`) and cross-checks it against both audio rows; the Android
summary reproduces the same decomposition independently. 1024 is also the documented
Qwen-VL minimum, which RTX's own summary quotes from the server startup warning
("Qwen-VL models require at minimum 1024 image tokens") while nonetheless recording
1036.

This is a bookkeeping error in a derived column, correctable without re-running
anything. The image encode workload was the same on all three devices. It still fails
the check as written.

### 7. `audio_tokens` — FAIL

| device | audio-30s | audio-10s | `prompt_tokens` 30s / 10s | tok/s implied |
|---|---|---|---|---|
| rtx | **1512** | **512** | 1540 / 540 | 50.4 / 51.2 |
| macbook | **1500** | **500** | 1540 / 540 | 50.0 / 50.0 |
| one-plus | **1500** | **500** | 1540 / 540 | 50.0 / 50.0 |

Same cause as check 6: RTX subtracted the 28-token audio instruction but not the
12-token chat template; Mac and Android subtracted both.

Against the ~1500 / ~500 prediction: Mac and Android land on it exactly, at 50.0
audio tokens per second of audio for both clips. RTX's 1512 / 512 is 0.8 % and 2.4 %
above the prediction and is an artefact of the derivation, not of the encoder.
`audio_seconds` is 30 / 10 on all three devices.

### 8. `mmproj_variant` coverage — PASS

Every device has `audio+vision` on all primary rows, plus both required Q4_K_M
control rows at n = 5:

| device | `audio+vision` rows | `none` / `text-512` | `vision-only` / `vision` |
|---|---|---|---|
| rtx | 150 | 5 | 5 |
| macbook | 150 | 5 | 5 |
| one-plus | 141 | 5 | 5 |

No row carries any other `mmproj_variant` value.

---

## GATE DECISION

Checks 5, 6 and 7 fail. Per the protocol, merging stops here.

Ranking the three by what they actually mean:

- **Check 5 is a real measurement divergence.** RTX prefilled 138 / 523 / 2058 tokens
  where the other two prefilled 128 / 513 / 2048. Different work was done. This
  cannot be fixed by editing a column; it affects `ttft_ms` and `prefill_tps` on 90
  RTX text rows and cannot be corrected without re-running those rows through
  `/completion`, or without an explicit decision to compare across a known 10-token
  offset and to caveat every text-mode latency comparison involving RTX.
- **Checks 6 and 7 are derived-column arithmetic.** `prompt_tokens` for `vision`,
  `audio-30s` and `audio-10s` is 1101 / 1540 / 540 on all three devices, identically.
  Only the subtraction differs. Recomputing RTX's `image_tokens` and `audio_tokens`
  as `prompt_tokens − instruction − 12` yields 1024 / 1500 / 500 and reconciles both
  checks against the other two devices with no re-measurement. That change is not
  applied here, because the gate says stop and report rather than work around.

---

## Coverage check

Grid is device × variant × `mmproj_variant` × mode. Cell contents are the rep count
for `thermal_state = sustained` unless marked.

### Primary grid — `mmproj_variant = audio+vision`

| variant | mode | rtx | macbook | one-plus |
|---|---|---|---|---|
| BF16 | text-128 | 5 | 5 | 5 |
| BF16 | text-512 | 5 | 5 | **2** |
| BF16 | text-2048 | 5 | 5 | **ABSENT** |
| BF16 | vision | 5 | 5 | **ABSENT** |
| BF16 | audio-30s | 5 | 5 | **ABSENT** |
| BF16 | audio-10s | 5 | 5 | **ABSENT** |
| Q8_0 | all 6 modes | 5 each | 5 each | 5 each |
| Q6_K | all 6 modes | 5 each | 5 each | 5 each |
| Q5_K_M | all 6 modes | 5 each | 5 each | 5 each |
| Q4_K_M | text-128 | 5 | 5 | 5 |
| Q4_K_M | text-512 | 5 | 5 | **15** (see below) |
| Q4_K_M | text-2048 | 5 | 5 | 5 |
| Q4_K_M | vision | 5 | 5 | 5 |
| Q4_K_M | audio-30s | 5 | 5 | 5 |
| Q4_K_M | audio-10s | 5 | 5 | 5 |

### Control grid

| variant | mmproj | mode | rtx | macbook | one-plus |
|---|---|---|---|---|---|
| Q4_K_M | none | text-512 | 5 | 5 | 5 |
| Q4_K_M | vision-only | vision | 5 | 5 | 5 |

### Cells that are ABSENT, not N/A

**There are zero N/A rows in any of the three CSVs.** Every one of the 471 rows is a
completed measurement. The four uncollected Android cells are absent from
`one-plus/results.csv` entirely; their N/A status and reason exist only as prose rows
in `one-plus/summary.md`.

| device | cell | status | reason given, and where |
|---|---|---|---|
| one-plus | BF16 / audio+vision / text-2048 | **ABSENT from CSV** | summary only: "battery floor reached; BF16 prefill is 1.42 tok/s, implying ~20-25 min per run" |
| one-plus | BF16 / audio+vision / vision | **ABSENT from CSV** | same |
| one-plus | BF16 / audio+vision / audio-30s | **ABSENT from CSV** | same |
| one-plus | BF16 / audio+vision / audio-10s | **ABSENT from CSV** | same |

The reason is quantitative — it names a measured prefill rate (1.42 tok/s, which is
confirmed in the 7 BF16 rows that do exist) and derives a per-run duration from it.
It satisfies the "no bare N/A" requirement in substance. It does not satisfy it in
the CSV, because there is no row to carry it. Any merge must add these four cells as
explicit N/A rows or they will silently disappear.

### Under-repped cells

| device | cell | reps | note |
|---|---|---|---|
| one-plus | BF16 / audio+vision / text-512 / sustained | **2** | below the 5-rep protocol; the summary states the block was stopped at the battery floor |
| one-plus | Q4_K_M / audio+vision / text-512 / **cold** | **3** | cold block cut short by the operator |
| one-plus | Q4_K_M / audio+vision / vision / **cold** | **1** | single run; no median is meaningful |

### A grouping collision that will corrupt the merge if not handled

`one-plus` `Q4_K_M / audio+vision / text-512 / sustained` holds **15 rows, not 5**.
They are three distinct server configurations, distinguished only inside the `notes`
column:

| `threads=` in notes | reps | decode_tps values |
|---|---|---|
| 6 (the baseline) | 5 | 8.84, 8.95, 8.97, 8.90, 8.19 |
| 4 (thread-sensitivity) | 5 | 6.12, 6.49, 6.55, 6.78, 6.30 |
| 8 (thread-sensitivity) | 5 | 4.92, 5.17, 5.10, 5.17, 4.87 |

The Phase 2 grouping key as specified — device × variant × `mmproj_variant` × mode ×
`thermal_state` — does not separate these. Taking a median over all 15 gives
6.49 tok/s, which is the `-t 4` cell and is not the Android Q4_K_M `text-512` decode
figure. The correct baseline is **8.90 tok/s** at `-t 6`. This needs a decision
before Phase 2 runs; the options are to extend the grouping key with a `threads`
field, or to exclude the `-t 4` and `-t 8` rows from `merged_medians.csv` while
keeping them in `merged_results.csv`.

---

## Deviation reconciliation

Every deviation from all three summaries, in one table. "Comparability" states
whether the deviation affects cross-device comparison of the merged numbers.

| # | device | what deviated | why | affects comparability |
|---|---|---|---|---|
| R-1 | rtx | Working directory contained Cyrillic characters, breaking the nvcc compiler-ID build step and `llama-tokenize -f`. Whole working set relocated to `C:\qolda-bench\`. | OS/toolchain Unicode path bug | No for measurements. **Possibly yes for check 5**: this is the same tool that produced the disputed +2 tokenizer reading. |
| R-2 | rtx | Build pinned to CUDA 12.6 (`-T cuda=12.6`, `-DCMAKE_CUDA_ARCHITECTURES=89`); v13.1 also installed but unused. | `native` arch detection failed under 13.1 with driver 572.16 | No |
| R-3 | rtx | `HF_HUB_DISABLE_XET=1` to force the classic HTTP download path. | Xet backend hung at 0 bytes twice | No |
| R-4 | rtx | `Q6_K` GGUF re-downloaded after a sha256 mismatch against the HF API (correct size, wrong content). | silent transfer corruption, caught pre-run | No. Caught before any measurement. |
| R-5 | rtx | 4 model files re-downloaded after an `rm -rf` ran alongside an unverified `cp -r` (OneDrive placeholder files copied at 0 bytes). | operator sequencing error, self-reported | No. Public re-downloadable weights, all hashes verified before any run. |
| R-6 | rtx | Windows power plan changed from Balanced to High performance before any measured run. Armoury Crate profile could not be read or set via CLI and is **unverified**. | ASUS hides stock plans | **Yes, weakly.** The Armoury Crate profile is an unknown on this device. |
| R-7 | rtx | **Only GPU package power logged** (`nvidia-smi power.draw`). CPU package power not captured. No HWiNFO64 or LibreHardwareMonitor. | not installed | **Yes. This is the power-boundary divergence.** |
| R-8 | rtx | `--parallel 1` set explicitly. | llama-server defaults to 4 slots; needed for batch-1 and correct KV accounting | No. Mac and Android set it too. |
| R-9 | rtx | `--no-mmap` **not** passed. | `-ngl 999` fully offloads; mmap affects only the load path | **Minor.** Mac and Android both ran `mmap=off` explicitly. RTX ran mmap on. |
| R-10 | rtx | Text sent via `/v1/chat/completions`. | not flagged as a deviation by RTX; identified here from `bench.py` | **Yes. This is check 5.** Undisclosed in the RTX summary. |
| R-11 | rtx | `encoder_ms` blank on all 160 rows. | llama-server reports no separate encode field on this build | Yes, uniformly — see below. |
| R-12 | rtx | Cold-start artefact retained: `run_idx=1` on every vision cell runs 2.1–2.5× the median TTFT, and 1.3–1.7× on audio. Root cause is that the 3 warm-ups used only `text-128`, so the first vision/audio request per session paid one-time CUDA graph init. | per protocol, outliers kept | **Yes.** RTX vision/audio TTFT medians run high relative to steady state. Mac and Android summaries do not report this pattern. |
| M-1 | macbook | `pmset powermode = 2` (High Power Mode), a non-default profile that raises sustained clocks and fan speed. Retained on operator instruction. | explicit instruction | **Yes.** Self-flagged as "best-case and not strictly comparable" if the other devices ran stock. |
| M-2 | macbook | `encoder_ms` blank on all 160 rows; encoder measured separately via `llama-mtmd-cli -v` and reported only in the summary, deliberately kept out of the CSV. | llama-server reports no encode field | Yes, uniformly. **Note: the Mac is the only device with direct encoder measurements, and they are not in the CSV.** |
| M-3 | macbook | **Text modes used raw `/completion`; vision and audio used `/v1/chat/completions`.** | to keep `prompt_n` directly comparable to 128/513/2048 | **Yes. This is the other half of check 5.** Disclosed. |
| M-4 | macbook | `--reasoning-format none` added. | without it the Thinking checkpoint routes `<think>` to `reasoning_content` and TTFT is mismeasured | No effect on token count or compute. Android set it too; **RTX did not.** |
| M-5 | macbook | Extra server flags `-b 2048 -ub 512 --parallel 1 --no-webui`. | defaults made explicit; single-stream enforced | No. Android matches. |
| M-6 | macbook | Closing idle baseline (0.719 W) contaminated by two commands run in its window; clean re-measure 0.572 W. Energy uses the opening 0.600 W baseline. | operator error, disclosed | No. No result depends on the contaminated value. |
| M-7 | macbook | `powermetrics` has 1 s timestamp resolution, so request-window slicing is quantised by up to ±1 s. Runs are 3.4–9 s. | tool limit | **Yes, weakly.** `avg_power_w` carries edge uncertainty on the Mac. |
| M-8 | macbook | `peak_rss_gb` in GiB (binary). | matches the protocol's file-size convention | Yes if mixed with decimal GB. All three devices need a stated unit. |
| M-9 | macbook | Memory via `ps rss` at 200 ms rather than `footprint`. | `footprint` too slow for the cadence | Minor |
| M-10 | macbook | Optional battery repeat set not run. | listed as "if time allows"; needs physical unplugging | No |
| M-11 | macbook | Screen brightness not recorded numerically; held fixed; `caffeinate -dims` used. | macOS 26 exposes no percentage without full Xcode | No. Display rail is outside the SoC boundary anyway. |
| M-12 | macbook | Passwordless sudoers rule added for `powermetrics`. | unattended sampling | No. **Action item: `sudo rm /etc/sudoers.d/qolda-powermetrics`.** |
| M-13 | macbook | Pre-existing `summary.md` preserved as `artifact_provenance.md`. | not reproducible from this run | No. **That file is not in the delivered folder.** |
| M-14 | macbook | No full Xcode; Command Line Tools only, SDK 15.5, Metal 4. | not installed | No. Metal backend built and ran. |
| M-15 | macbook | 3 BF16 audio rows saw real page-outs (max 15,692 pages ≈ 257 MB); 22 further rows saw compression with `swapout = 0`. All flagged `SWAP-AFFECTED` and retained. | disclosed, not discarded | Minor. Measured cost 0.4–0.7 % on decode. |
| OP-1 | one-plus | **Power source substituted.** `/sys/class/power_supply/battery/*` returns Permission denied; no ODPM rails. Used `cmd battery get -f current_now` × `dumpsys battery voltage`. | forced by Android 16 / OxygenOS SELinux | **Yes. This is the power-boundary divergence.** |
| OP-2 | one-plus | **Units are mA and mV, not the µA/µV the protocol assumed.** µA×µV gives 0.000000 W; mA×mV gives 0.406 W, inside the 0.3–0.8 W sanity band. | OEM register convention | Yes if not applied. Applied correctly here. |
| OP-3 | one-plus | Airplane mode on **with WiFi deliberately left up** as the measurement transport. | full airplane mode removes ADB | Minor. WiFi is up during the idle baseline too, so it largely cancels in `avg − idle`. |
| OP-4 | one-plus | Sampling is discrete `adb shell` invocations (~68 ms each), memory at 500 ms, power/thermal ~1 Hz. | operator constraint: nothing installed on device | **Yes, weakly.** The sampling traffic is itself a load on the measured device. |
| OP-5 | one-plus | `-ngl 999` omitted. | no-op on a CPU-only build | No |
| OP-6 | one-plus | **Thermal design restructured.** Full matrix run as `sustained`; cold reduced to Q4_K_M × {text-512, vision, audio-30s} × 3 reps; one 20-minute decay curve planned. | literal protocol implies ~170 cooldowns ≈ 28 h | **Yes.** See the correction below. |
| OP-7 | one-plus | BF16 moved to last in variant order. | slowest, likeliest to thrash | No |
| OP-8 | one-plus | Per-run zone temperatures carried in `notes` as `tz_start[...]` / `tz_end[...]`. | the 26-column schema has no temperature column | No. Recoverable by parsing. |
| OP-9 | one-plus | `encoder_ms` blank on all 151 rows. | llama-server reports no encode field | Yes, uniformly. |
| OP-10 | one-plus | **Two columns appended: `avg_power_w_raw` and `power_samples_used`.** | so the power correction is visible per row | No. Appended after column 26, so the leading schema is positionally compatible. |
| OP-11 | one-plus | Direct TCP to the phone's WiFi address instead of `adb forward`. | the tunnel cost 2–17 % of client-side decode and once produced 0.36 tps client-side against 7.38 tps server-side | **Improves** comparability. Client/server agreement 0.990–0.998 after. |
| OP-12 | one-plus | Memory sampling held at 500 ms after an attempt to slow it to 2 s made delivery worse. | recorded as the evidence for OP-13 | No |
| OP-13 | one-plus | Host-side `ping -i 0.05` keepalive holds the WiFi radio active for the whole session. | Android WiFi power-save delivered streamed chunks in DTIM bursts, deflating client-side decode | Minor. Present during the idle baseline too, so it cancels in `avg − idle`. **Side effect: it eliminated the 0 mA sentinels entirely** (0 of 105 vs 19 of 88 before). |
| OP-14 | one-plus | `VmHWM` reset via `/proc/<pid>/clear_refs` before every run. | one server process serves 30 runs; without the reset `peak_rss_gb` would be monotonically non-decreasing within a block | **Improves** correctness. Android `peak_rss_gb` is a true per-run peak; the other two devices sample RSS at 200 ms instead. |
| OP-15 | one-plus | Every row carries `server_decode_tps` and a client/server ratio in `notes`; rows below 0.95 flagged `TRANSPORT-AFFECTED` (3 rows). | `decode_tps` is defined client-side | Yes, disclosed per row. **`ttft_ms` and `total_ms` still contain transport overhead that `decode_tps` does not** — ~1–2 % on audio/vision, proportionally larger on `text-128`. |

### The four deviations flagged in the task, checked against the data

**Power measurement boundary differs by device — CONFIRMED, and it is the single most
important item in this report.**

| device | boundary | source | `idle_power_w` in CSV |
|---|---|---|---|
| rtx | **GPU package only** | `nvidia-smi --query-gpu=power.draw` | 11.139 W (single value, all 160 rows) |
| macbook | **SoC package** (CPU Power + GPU Power, excludes display and DRAM rails) | `powermetrics -s cpu_power,gpu_power` | 0.6 W (single value, all 160 rows) |
| one-plus | **Whole-device battery draw** | BatteryManager `current_now` × `dumpsys battery voltage` | 0.459 / 0.474 / 0.5 W (three values) |

These are three different quantities. The RTX figure excludes the CPU package
entirely (R-7 states this in terms: "total laptop wall power is higher than the
`avg_power_w` / `energy_j_per_1k_tok` figures reported"). The Mac figure excludes
display and DRAM. The Android figure includes everything the battery feeds, including
the screen-off SoC, the WiFi radio and the display controller. `avg_power_w` and
`energy_j_per_1k_tok` must never appear in a single table column across these three
devices without a boundary column, and the Phase 3 `power_boundary` column is the
mechanism for that.

**Android power correction — CONFIRMED, both columns exist.**

`avg_power_w_raw` and `power_samples_used` are present and populated on all 151
Android rows, appended after the protocol's 26 columns. The median correction is
**+0.24 W** (`avg_power_w − avg_power_w_raw`), range −0.12 W to +1.78 W. 15 rows
carry `UNRELIABLE POWER: only N usable samples (<8)` in `notes`.

The correction discards a lead-in and the 0 mA sentinels. The per-row `notes` record
the lead-in explicitly, e.g. `power_sampled_at=0.25Hz lead_in=8.0s tail=0.0s`.

**One discrepancy found here.** The Android summary states
"`idle_power_w` = 0.433 W — mean over all samples including zeros … This is the value
in `results.csv`." It is not. `one-plus/results.csv` carries three distinct
`idle_power_w` values — 0.459 W (84 rows), 0.474 W (42 rows), 0.5 W (25 rows) — and
0.433 W appears on no row. Since `energy_j_per_1k_tok = (avg_power_w − idle_power_w)
× decode_seconds / generated_tokens × 1000`, every Android energy figure was computed
against a baseline other than the one the summary documents. Three values suggests
the baseline was re-measured between blocks, which is defensible, but it is
undocumented. **Any Android energy claim must state that it rests on a per-block
`idle_power_w` of 0.459/0.474/0.500 W, not the 0.433 W in the summary.**

**Android units mA/mV — CONFIRMED and documented** (OP-2). The summary shows the
sanity check that forced it: µA×µV gives 0.000000 W, six orders of magnitude low;
mA×mV gives 0.406 W, inside the protocol's 0.3–0.8 W band.

**"No cold or burst measurements were taken on Android" — THIS IS NOT WHAT THE DATA
SHOWS. Correction required.**

`one-plus/results.csv` contains **4 rows with `thermal_state = cold`**:

| variant | mmproj | mode | reps | decode_tps |
|---|---|---|---|---|
| Q4_K_M | audio+vision | text-512 | **3** | median 9.01 |
| Q4_K_M | audio+vision | vision | **1** | 7.52 |

147 of 151 Android rows are `sustained`; 4 are `cold`. The statement that every
Android row is `sustained` and that no row is labelled `cold` is false as delivered.

What is true is the narrower claim: the **thermal decay run was not executed**
(`thermal_decay.csv` is absent, and the Android summary says so in terms: "The
20-minute decay curve, which would have resolved this properly, was not run"), and
the cold block was **cut short by the operator after 4 of 9 planned runs** —
`audio-30s` cold was never run and the `vision` cold cell is a single measurement.

This changes what Phase 4 item 4 can say. A cold/sustained comparison does exist for
two cells, and the Android summary already computes it: text-512 is +1.2 % cold
(9.01 vs 8.90), vision is +12.6 % cold (7.52 vs 6.68, n=1 cold). Whether a
throttling ratio should be computed from a 3-run and a 1-run cold sample is a
judgement call, and the instruction not to compute one may still be the right call
given the sample sizes. But the premise it was based on — that no cold data exists —
does not hold, and the report should say what is there rather than assert absence.

**BF16 on Metal — it was NOT unsupported. It ran.**

The Mac summary states it directly: "BF16 works on Metal. It was neither refused nor
silently downgraded. It loads, runs, and sustains 28.5 tok/s. No F16 substitution was
made or needed." The CSV agrees: all 30 BF16 rows are present at n=5 across all six
modes, with `peak_rss_gb` 10.2–10.7 GiB.

BF16 also ran on Android, permanently swapped: 7.67 GB resident plus 4.18 GB in zram,
decode 1.14–1.17 tok/s, TTFT 93,082 ms on the 128-token prompt. It did not OOM and
was not refused. Seven rows exist. The four uncollected BF16 modes were a battery and
time limit, not a failure.

**Audio path fallback to `llama-mtmd-cli` — did not happen on any device.**

The string `mtmd` appears **zero times** in all three `results.csv` files. All three
summaries state the `input_audio` content block worked natively through
`llama-server` and the fallback was never needed. The Mac used `llama-mtmd-cli -v`
separately to measure `encoder_ms`, and deliberately kept those numbers out of the
CSV so the two sources are never mixed within a mode.

### Deviations present in the data but absent from the summaries

1. **RTX sent text through `/v1/chat/completions`** (`rtx/bench.py:122-126`). The RTX
   summary lists ten deviations and this is not among them, although §3 discusses the
   +8 template overhead as an observation. Given that the Mac explicitly flagged the
   opposite endpoint choice as a deviation, the RTX side of it should have been
   flagged too. It is the direct cause of check 5.
2. **RTX derived `image_tokens` and `audio_tokens` without subtracting the 12-token
   template overhead**, while its own §5 acknowledges the risk ("if the chat template
   adds any wrapper tokens specific to multi-part messages … that overhead is folded
   into these derived counts"). The other two devices resolved it; RTX did not, and
   recorded the unresolved figures as the column value.
3. **RTX ran with mmap on** while both other devices ran `mmap=off` and record it in
   every row's `notes`. RTX's deviation 9 argues mmap is irrelevant under full
   offload, which is reasonable, but the configurations differ and only two of three
   devices carry the flag in the data.
4. **RTX did not set `--reasoning-format none`**, which both other devices set and
   the Mac flagged as necessary to avoid mismeasuring TTFT on a Thinking checkpoint.
   RTX's `ttft_ms` is computed from the "first content-bearing SSE chunk" per its own
   harness description, which may handle it, but the server configuration differs.
5. **Android `idle_power_w` is 0.459 / 0.474 / 0.500 W in the CSV, not the 0.433 W
   the summary documents.** Detailed above.
6. **The Android thread-sensitivity rows (`-t 4`, `-t 8`) are stored in the same
   variant/mode/thermal_state cell as the `-t 6` baseline**, distinguished only by a
   `threads=` token inside `notes`. The summary presents them as a separate
   supplementary table, so the intent is clear, but the CSV schema does not encode it
   and any naive grouping will mix them.
7. **Android BF16 has no N/A rows for its four uncollected cells.** The summary's
   matrix shows them with reasons; the CSV has no rows at all.

### Cross-device disagreements that look like measurement error, not hardware

Flagged, not resolved.

1. **The tokenizer conflict.** RTX reports 130 / 515 / 2050 from
   `llama-tokenize --no-bos` on patched `ea63b4d`; Mac and Android both report
   128 / 513 / 2048 from the same tool on the same commit with the same input hash.
   Tokenisation is backend-independent, so this cannot be a CUDA/Metal/ARM effect.
   Two against one.
2. **`encoder_ms` is blank on all 471 rows**, on all three devices, for the same
   stated reason. The Phase 4 item that asks for `encoder_ms` versus `ttft_ms` for
   audio-30s against audio-10s cannot be answered from the CSV column on any device.
   It can be answered from `ttft_ms` alone, and the Mac and Android summaries each
   contain an independent encoder decomposition, but those numbers live in prose and
   the Mac's direct `llama-mtmd-cli` figures are deliberately outside the CSV.
3. **RTX `peak_rss_gb` is ~2.79 GB** on rows where the Mac reports 5.32–10.7 GiB and
   Android 3.33–7.92 GB. This is expected and not an error — under `-ngl 999` the
   weights are in VRAM and the RTX RSS figure is host-side process memory only, while
   the other two devices are unified/CPU and their RSS is the whole working set. It
   is called out because a merged memory column that mixes RTX `peak_rss_gb` with the
   other two would be meaningless. For RTX the memory figure is `peak_vram_gb`
   (7.106–12.473 GiB); for the other two it is `peak_rss_gb`, with `peak_vram_gb`
   literally reading `unified (no discrete VRAM)`.
4. **The Mac ran in a non-default High Power Mode (M-1) while the RTX Armoury Crate
   profile is unverified (R-6).** Neither device's performance profile is a matched
   control for the other. Both summaries disclose this about themselves.

---

## What would clear the gate

1. **Check 5.** A decision on whether to re-run the 90 RTX text rows through
   `/completion`, or to accept the 10-token offset and caveat every text-mode TTFT
   and prefill comparison involving RTX. This is the only item that needs
   re-measurement.
2. **Checks 6 and 7.** Authorisation to recompute RTX's `image_tokens` and
   `audio_tokens` as `prompt_tokens − instruction − 12`, giving 1024 / 1500 / 500 and
   matching the other two devices. No re-measurement needed. The change would be
   recorded as a derived-column correction, with the original values preserved.
3. **The Android grouping collision.** A decision on whether `merged_medians.csv`
   should key on `threads` as well, or exclude the `-t 4` and `-t 8` rows.
4. **The four absent Android BF16 cells.** A decision on whether to synthesise
   explicit N/A rows carrying the summary's quantitative reason, so they survive the
   merge instead of vanishing.
5. **Android `idle_power_w`.** Confirmation of which baseline each block used, or
   agreement to report the three CSV values as-is and drop the 0.433 W figure from
   the write-up.
