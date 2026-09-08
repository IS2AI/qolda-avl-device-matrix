# Qolda-AVL-5B-GGUF: measured device matrix

Data, code and reports behind the device matrix for `issai/Qolda-AVL-5B-GGUF`.
Three device classes, five quantization variants, six workload modes, five
repetitions per cell, plus two control cells per device. **471 measured runs.**

Every number in every report traces to a row in a device CSV. Nothing is
interpolated, modelled, or estimated. Cells that were not measured are recorded
as absent rather than filled in.

These are speed, memory and energy measurements. Nothing here evaluates output
quality.

## Start here

| | |
|---|---|
| [`merged_results.csv`](merged_results.csv) | All 471 runs in one table. `device_id` / `source_file` / `source_row` point every row back at its source CSV. |
| [`cross_device_summary.md`](cross_device_summary.md) | The cross-device comparison: measurement boundaries, which metrics are comparable across devices, the performance tables, and the limits. |
| [`validation_report.md`](validation_report.md) | Proof the three devices ran the same thing: commit, artifact hashes, generation settings, prompt token counts, coverage grid, every protocol deviation. |
| [`MANIFEST.md`](MANIFEST.md) | sha256, size and row count for every file. |
| [`REVIEW_REPLY.md`](REVIEW_REPLY.md) | Reply text for the review thread, Russian and English. |

## Headline

Q4_K_M with the audio+vision projector, sustained thermal state, median of 5 runs.

| | RTX 4090 Laptop (CUDA) | M4 Pro (Metal) | Snapdragon 8 Gen 3 (ARM CPU) |
|---|---:|---:|---:|
| decode, text-128 | 91.4 tok/s | 75.8 tok/s | 9.78 tok/s |
| decode, vision | 88.9 tok/s | 72.3 tok/s | 6.68 tok/s |
| decode, audio-30s | 89.0 tok/s | 70.7 tok/s | 5.85 tok/s |
| TTFT, text-128 | 0.243 s | 0.163 s | 2.93 s |
| TTFT, vision | 1.37 s | 2.26 s | 161 s |
| TTFT, audio-30s | 1.85 s | 2.50 s | 135 s |
| peak memory | 7.11 GiB VRAM | 5.32 GiB unified | 5.49 GiB RSS |
| average power | 102 W | 24.3 W | 7.32 W |

The three power figures are **not comparable**: they are measured at three
different hardware boundaries. See below.

The phone runs the model. Text generation at 9.78 tok/s is usable. The
multimodal path is not: 161 s to first token on an image, because the vision
encoder alone costs 133 to 135 s on CPU.

## Devices

| id | device_class | hardware | backend | power boundary | rows |
|---|---|---|---|---|---:|
| D1 | `discrete-gpu-laptop` | ASUS ROG Zephyrus G16, NVIDIA RTX 4090 Laptop GPU, 16 GB VRAM, Windows 11 | CUDA | GPU package only (`nvidia-smi power.draw`) | 160 |
| D2 | `unified-memory-laptop` | MacBook Pro, Apple M4 Pro (10P + 4E CPU, 20 GPU cores), 24 GB unified | Metal | SoC package (`powermetrics` CPU + GPU) | 160 |
| D3 | `flagship-smartphone` | OnePlus 13R (CPH2691), Snapdragon 8 Gen 3, 16 GB LPDDR5X, Android 16 | CPU (ARM NEON / i8mm) | whole-device battery (mA x mV) | 151 |

Those three boundaries enclose different hardware. D1 does not capture CPU
package power at all, so its wall draw is higher than the figure above. Energy
is labelled with its boundary everywhere it appears and is never pooled into one
cross-device table.

## Layout

```
merged_results.csv        all 471 rows, three devices, one schema
cross_device_summary.md   cross-device comparison and synthesis
validation_report.md      identity checks, coverage grid, deviations
MANIFEST.md               sha256 for every file
REVIEW_REPLY.md           reply text for the review thread
LICENSE                   Apache-2.0, for the code
LICENSE-DATA              CC-BY-4.0, for the results and reports
NOTICE.md                 copyright and third-party terms
verify.sh                 checks hashes and re-derives the merged CSV
tools/merge_results.py    builds merged_results.csv from the three device CSVs

protocol/                 inputs consumed byte-identically by all three devices
  prompts_text.txt          Kazakh text prompts at 128 / 513 / 2048 tokens
  source_kk.txt             the Kazakh corpus the prompts were cut from
  bench_image.jpg           fixed vision input
  bench_audio_10s.wav       fixed 10 s audio input
  bench_audio_30s.wav       fixed 30 s audio input
  qwen3avl-support.patch    patch applied on top of llama.cpp ea63b4d
  make_prompts.py           builds prompts_text.txt from source_kk.txt
  fetch_source.py           fetches the corpus
  parse_prompts.py          reads the prompts back and checks token counts
  device_briefs/            the per-device measurement brief

rtx/                      Device 1
  results.csv  summary.md  bench.py
  setup.ps1  run.ps1        PowerShell: this device ran on Windows

macbook/                  Device 2
  results.csv  summary.md
  bench.py                  driver; writes results.csv and raw_runs.jsonl
  bench_lib.py              request bodies, generation settings, metric extraction
  aggregate.py              reads results.csv, prints medians
  raw_runs.jsonl            per-run records behind every CSV row
  env.json  file_manifest.json  artifact_provenance.md
  idle_baselines.json  idle_clean.json
  setup.sh  run.sh

one-plus/                 Device 3
  results.csv  summary.md
  bench.py                  driver; writes results.csv and raw_runs.jsonl, resumable
  bench_lib.py              request bodies, generation settings, metric extraction
  power_calc.py             battery power derivation and idle subtraction
  calibrate_power.py        sampler calibration against the battery register
  aggregate.py              reads results.csv, prints medians
  token_census.py           derives image and audio token counts from prompt_n
  token_census.json         census output, incl. the 12-token template overhead
  raw_runs.jsonl            per-run records behind every CSV row
  raw_runs_1hz_registercal.jsonl   sampler validation run
  env.json                  incl. per-location idle power
  setup.sh  run.sh
```

## What was held identical

Verified in `validation_report.md` from the source files, not from prose.

- llama.cpp commit `ea63b4d32ea1b66bdbe369be7f9443f6c00f8b31` on all three
  devices, with `qwen3avl-support.patch` applied on all three
  (patch sha256 `bb27de1e…`, 8 files changed, applied with zero fuzz everywhere).
- The same five GGUF variants and two mmproj files, checked by sha256:
  BF16 7.498, Q8_0 3.986, Q6_K 3.079, Q5_K_M 2.691, Q4_K_M 2.326 GiB;
  audio+vision mmproj 2.043 GiB, vision-only 0.779 GiB.
- Generation settings, read out of the code on all three devices:
  `n_predict=256, ignore_eos=true, temperature=0.7, top_p=0.95, top_k=20,
  seed=1234, n_ctx=4096, cache_prompt=false`.
- The two Kazakh instructions, byte-identical on all three devices.
- The image and both audio files, byte-identical on all three devices.
- Memory reported in GiB by all three devices.
- CSV schema: the protocol's 26 columns in the same order on all three.
  Device 3 appends `avg_power_w_raw` and `power_samples_used` after them.

## What was not identical

Read the tables with these in mind. Full detail in `validation_report.md`.

- **Text endpoint.** D1 sent text through the chat endpoint, so its text prompts
  carry the chat template and measure 138 / 523 / 2058 tokens against
  128 / 513 / 2048 on D2 and D3. Decode throughput is unaffected and is
  tabulated across all three. Text TTFT and prefill are tabulated separately.
- **Multimodal token counts.** D1 reports `image_tokens` 1036 and `audio_tokens`
  1512 / 512 because it did not subtract the 12-token template overhead. D2 and
  D3 report 1024 and 1500 / 500. The underlying media are the same files.
- **mmap.** D1 ran with mmap on; D2 and D3 ran `--no-mmap` and record `mmap=off`
  in every row. Under `-ngl 999` this affects the load path.
- **Power boundaries.** Three different boundaries, listed above.
- **Coverage.** D3 is short of the full grid: four BF16 cells (`text-2048`,
  `vision`, `audio-10s`, `audio-30s`) were never run and are absent from the CSV;
  `BF16 / text-512` has 2 repetitions instead of 5. D3 also carries 4 `cold` rows
  and a thread sweep at `-t 4 / 6 / 8` under `Q4_K_M / text-512 / audio+vision`.
  **The published D3 baseline is `-t 6`.** Grouping D3 rows without filtering on
  the thread count in `notes` silently mixes the three sweeps together.
- **Ambient temperature.** Recorded for D3 at location 1 only (23 C). Not
  measured at locations 2 and 3.
- **`encoder_ms` is empty in all 471 rows on all three devices.** The column is
  in the schema and no device populated it. Where `cross_device_summary.md`
  reports encoder cost it is *derived*, by subtracting LLM prefill at that
  cell's measured text prefill rate from the measured `ttft_ms`, using the same
  subtraction on all three devices. On D2 the derived figures were cross-checked
  against a direct `llama-mtmd-cli` measurement: 458 ms and 460 ms measured
  against 0.50 s and 0.56 s derived.

## Scope

The measured grid is three device classes by five GGUF variants
(**BF16, Q8_0, Q6_K, Q5_K_M, Q4_K_M**) by six modes, all through llama.cpp at
commit `ea63b4d` with the Qwen3-AVL patch applied.

All 471 rows are completed measurements; none is a partial or failed run.
Four BF16 cells on Device 3 (`text-2048`,
`vision`, `audio-10s`, `audio-30s`) were not run: BF16 prefill on that device is
1.42 tok/s, putting a single run at 20 to 25 minutes and into the battery floor.
The reason is recorded in `one-plus/summary.md`. Those rows are absent from the
CSV and are not filled in by estimation anywhere.

## Reproducing

Each device has a `setup` script (build the patched llama.cpp, download the
model files, stage the fixed inputs) and a `run` script (preflight, then the
matrix). Model weights are not in this repo; the setup scripts download them
from `issai/Qolda-AVL-5B-GGUF`.

```bash
# Device 2, Apple M4 Pro
cd macbook && ./setup.sh && ./run.sh

# Device 3, OnePlus 13R (harness runs on the Mac, drives the phone over wireless ADB)
export NDK=/path/to/android-ndk ADB_SERIAL=<phone-ip>:5555
cd one-plus && ./setup.sh && ./run.sh
```

```powershell
# Device 1, Windows / RTX 4090
cd rtx; .\setup.ps1; .\run.ps1
```

Three things the scripts cannot do for you:

1. **D2 needs sudo** for `powermetrics`. `bench.py` parses `power.log`; it does
   not start the sampler, and aborts with `FATAL: no power samples` without one.
   `run.sh` starts it and stops it on exit. The original runs used a passwordless
   sudoers rule; if you re-add one, remove it afterwards
   (`sudo rm /etc/sudoers.d/qolda-powermetrics`).
2. **D3 needs the phone unplugged**, screen off, on wireless ADB. Battery draw is
   the power boundary and reads garbage while charging; `run.sh` refuses to start
   if the phone is on AC or USB power. The transport is a direct TCP connection,
   deliberately not `adb forward`, which tunnels through adb's multiplexing and
   distorts TTFT.
3. **D1 hardcodes `C:\qolda-bench\llama.cpp\...\llama-server.exe`** (`bench.py`
   line 17). The working set was relocated there because building under a
   OneDrive-synced folder broke nvcc's compiler-ID step. Keep that path or edit
   the constant.

The setup and run scripts are transcriptions of the commands recorded in each
device's `summary.md` under "Exact commands run". They have not been re-executed
end to end from this repo, because that needs the hardware. They use
`set -euo pipefail` and fail loudly on a missing prerequisite rather than
producing partial rows.

To check the published data without any of the above:

```bash
./verify.sh
```

That checks every file against `MANIFEST.md`, re-derives `merged_results.csv`
from the three device CSVs and round-trips all 12,548 cells, and confirms the
three devices report one commit.

## Metric definitions

| metric | definition |
|---|---|
| `ttft_ms` | first streamed chunk minus send time |
| `prefill_tps` | `prompt_n / prompt_ms`, as reported by the server |
| `decode_tps` | `(gen_tokens - 1) / (t_last - t_first)` |
| `peak_rss_gb` | peak resident set size, GiB |
| `peak_vram_gb` | peak VRAM, GiB (D1 only) |
| `avg_power_w` | mean power over the run at that device's boundary, idle subtracted |
| `energy_j_per_1k_tok` | `avg_power_w` integrated over decode, per 1000 generated tokens |
| `encoder_ms` | empty on all three devices; see above |

On D3, `peak_rss_gb` **inverts** under zram swap: a variant that does not fit
shows a *lower* RSS than one that does, because pages are compressed out of
residency. Read D3 memory figures together with the memory section of
`cross_device_summary.md`.

## Model files

Not in this repo (~19 GiB). They are the published
[`issai/Qolda-AVL-5B-GGUF`](https://huggingface.co/issai/Qolda-AVL-5B-GGUF)
artifacts, identified by sha256 in `validation_report.md` and
`macbook/file_manifest.json`. Device 2's `power.log` (142 MB of raw
`powermetrics` output) is also excluded; the aggregated per-run figures it
produced are in `macbook/raw_runs.jsonl`.

## Funding

This work was developed as part of the project funded by the Ministry of Science and
Higher Education of the Republic of Kazakhstan under Grant No. BR24993001, "Creation of
a Large Language Model (LLM) to Support the Kazakh Language and Advance Technological
Development."

## License

Code is licensed under the Apache License 2.0 (`LICENSE`). Measurement results and input
artifacts are licensed under CC-BY-4.0 (`LICENSE-DATA`). Third-party material, including
the llama.cpp patch and the FLEURS-derived audio, is subject to its own terms; see
`NOTICE.md`.

## Citation

If you use this benchmark, please cite the model paper:

    @article{arystanbekov2026qolda,
      title   = {Extending a Vision--Language Model with Audio Understanding:
                 Introducing Qolda-AVL for the Kazakh Language},
      author  = {Arystanbekov, Batyr and Maxutov, Aidar and Nurimanov, Assanali
                 and Varol, Huseyin Atakan},
      journal = {Big Data and Cognitive Computing},
      volume  = {10},
      number  = {6},
      pages   = {192},
      year    = {2026},
      doi     = {10.3390/bdcc10060192}
    }
