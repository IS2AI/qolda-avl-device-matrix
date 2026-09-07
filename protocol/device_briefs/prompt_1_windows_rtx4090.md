# Qolda-AVL-5B deployment benchmark — Device 1: Windows / RTX 4090 Mobile

You are benchmarking `issai/Qolda-AVL-5B-GGUF` for a deployment paper.
Produce a measured results table. Follow this protocol exactly. Do not substitute
your own methodology. If a step is impossible on this device, do not skip it
silently — record it in the notes column and tell me.

**Run this device FIRST.** The audio patch was developed and demonstrated on CUDA,
so this is the lowest-risk platform. Validate the whole pipeline here before the
Mac and Android runs start.

---

## MODEL

Repo: `issai/Qolda-AVL-5B-GGUF`

Variants, in this order:

| Variant | Path | Size |
|---|---|---|
| BF16 | `BF16/Qolda-AVL-5B-BF16.gguf` | 8.1 GB |
| Q8_0 | `Q8_0/Qolda-AVL-5B-Q8_0.gguf` | 4.3 GB |
| Q6_K | `Q6_K/Qolda-AVL-5B-Q6_K.gguf` | 3.3 GB |
| Q5_K_M | `Q5_K_M/Qolda-AVL-5B-Q5_K_M.gguf` | 2.9 GB |
| Q4_K_M | `Q4_K_M/Qolda-AVL-5B-Q4_K_M.gguf` | 2.5 GB |

Projectors (`mmproj/` in the same repo):
- `mmproj-Qolda-AVL-5B-F16.gguf` — 2.2 GB, audio+vision. **Use this for all primary rows.**
- `mmproj-Qolda-AVL-5B-vision-only-F16.gguf` — 0.8 GB, vision only. Control rows only.

Architecture context: LLM is `qwen3vl` (36 layers, from Qwen3-VL-4B-Thinking); the
audio branch is a fine-tuned Whisper-large-v3-turbo encoder with DeepStack injection.
Encoders are always F16 and do not shrink with LLM quantization.

Record for every file used: exact filename, size in GiB, and the first 12 chars of
its sha256.

## BUILD — PATCHED llama.cpp IS REQUIRED

```bash
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
git checkout ea63b4d
git apply /path/to/qwen3avl-support.patch   # from llama.cpp-patch/ in the HF repo
cmake -B build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build -j --target llama-server llama-mtmd-cli llama-tokenize
```

- Commit `ea63b4d` is mandatory and must be identical on all three devices.
- Record: whether the patch applied cleanly, any conflicts, CUDA toolkit version,
  driver version, MSVC/clang version.
- **If the patch fails to apply or the build fails, STOP and report the error
  verbatim.** Do not fall back to stock llama.cpp. A stock build silently loses
  audio and the resulting rows would look like model failures rather than build
  failures.

## FIXED ARTIFACTS — verify before running

```
bench_image.jpg      d45840444cdef3c8d81eaa73c720f78e49fd3274c510fc49fc12665c43bb2330
prompts_text.txt     bb5c5cf054819d5775533e5fb8d2914196865351b1c5144fe7bdee35759dcc09
bench_audio_30s.wav  94c91da6916aa32b9ba6cd5e602a7eb941c3b2b637f46a1744dff7a8602bbbc7
bench_audio_10s.wav  c00cefb4f2d1c942f02eedebbc21dee4ccbc90cd1b2e08a40f18f162cfa77d0c
```

If any hash differs, stop and tell me. Do not regenerate these locally and do not
substitute your own. They are shared across all three devices and any divergence
silently breaks the comparison.

`prompts_text.txt` holds three prompts introduced by **opening markers only**:

```
<<<PROMPT_128>>>
<<<PROMPT_512>>>
<<<PROMPT_2048>>>
```

There are **no closing markers**. Each prompt body runs from the line after its
marker until the next `<<<PROMPT_` line or EOF. Split on that, strip the marker
lines, and strip trailing whitespace from each body. Send the body only.

Verify after parsing that you recovered exactly 3 non-empty prompts. If you get a
different number, stop and report it rather than guessing at the format.

## WORKLOADS

Six primary cells per variant:

| Mode | Input |
|---|---|
| text-128 | `<<<PROMPT_128>>>` body — 128 tokens |
| text-512 | `<<<PROMPT_512>>>` body — **513 tokens actual** |
| text-2048 | `<<<PROMPT_2048>>>` body — 2048 tokens |
| vision | `bench_image.jpg` (1024x1024) + fixed Kazakh instruction |
| audio-30s | `bench_audio_30s.wav` — 16 kHz mono s16le, 480000 frames, expect ~1500 audio tokens |
| audio-10s | `bench_audio_10s.wav` — bit-exact prefix of the 30 s file, 160000 frames, expect ~500 audio tokens |

Fixed vision instruction (identical on all devices):
```
Суреттегі нысандарды, олардың өзара орналасуын, түстері мен көрінетін жазуларды егжей-тегжейлі сипаттап бер.
```

Fixed audio instruction (identical on all devices):
```
Аудиодағы сөйлеуді сөзбе-сөз жазып шық.
```

Both strings are frozen. Do not reword, retranslate, or "fix" them.
Reference token counts (llama-tokenize, --no-bos): vision 65, audio 28.
Confirm against the server-reported counts and report any divergence.

## GENERATION SETTINGS — identical on every device

```
n_predict   = 256
ignore_eos  = true      <-- critical
temperature = 0.7
top_p       = 0.95
top_k       = 20
seed        = 1234
n_ctx       = 4096
batch size  = 1         (single stream; this is on-device inference)
cache_prompt = false    (prompt caching would fake the TTFT)
--no-mmap when weights sit in system RAM; record whether mmap was on or off
```

The base model is Qwen3-VL-4B-**Thinking**. It emits reasoning tokens before its
answer, and greedy decoding on Qwen3 thinking checkpoints can loop. `ignore_eos`
with a fixed `n_predict` makes every run emit exactly 256 tokens regardless of
content, so throughput windows are identical by construction.

**These are speed measurements, not quality measurements.** Do not attempt to
evaluate output quality — the model card already provides perplexity, KLD, and
top-1 agreement for every quant. State the use of `ignore_eos` explicitly in
summary.md.

## HARNESS — write `bench.py`

For each measured run:

1. Start `llama-server` with the target variant and `--mmproj`, wait for readiness,
   then issue 3 warm-up requests that are discarded.
2. Issue the measured request with `stream=true`.
3. `ttft_ms` = time from request send to arrival of the first token chunk.
4. `decode_tps` = (generated_tokens - 1) / (t_last_chunk - t_first_chunk).
5. `prefill_tps` = prompt_tokens / prompt_ms, from the server's `timings` object in
   the final chunk. Also record raw `prompt_n`, `prompt_ms`, `predicted_n`,
   `predicted_ms`.
6. `encoder_ms`: image or audio encode latency, separately, where the server reports
   it. If it does not, leave the column blank and note that encode time is folded
   into `ttft_ms`.
7. Sample memory and power throughout the request window at 200 ms. Record the
   **peak** memory and the **mean** power over that window only, not over the whole
   script.
8. Restart the server between variants. Never benchmark two variants from one process.

Audio input goes through the OpenAI-compatible chat completions endpoint as an
`input_audio` content block with base64 WAV. If `llama-server` rejects audio input,
fall back to `llama-mtmd-cli --audio`, take timings from its stderr, and mark those
rows `notes = "timings from llama-mtmd-cli"`. Do not mix the two sources within a
mode without flagging it.

## REPETITIONS

5 measured runs per (variant x mode). Report median with min–max range. Keep
outliers and note them; do not discard after the fact.

## SUPPLEMENTARY CONTROL ROWS — Q4_K_M only, 5 runs each

- **(a)** `text-512` with **no `--mmproj` at all**. Isolates the memory cost of
  carrying the projector in a text-only deployment.
- **(b)** `vision` with `mmproj-Qolda-AVL-5B-vision-only-F16.gguf` (0.8 GB).
  Quantifies the 1.4 GB penalty of carrying the audio branch.

Set `mmproj_variant` to `none` and `vision-only` on these rows. All primary rows are
`audio+vision`.

## TOKEN COUNTS — record once, report in summary.md

- Image tokens produced for `bench_image.jpg`.
- Audio tokens for each WAV. Expected ~50 tokens/second, so ~1500 for 30 s and
  ~500 for 10 s.
- Actual prompt tokens for each text prompt. Expected 128 / 513 / 2048.
  The `text-512` mode label is an identifier only; that prompt genuinely tokenizes
  to **513** tokens (a BPE merge makes 512 exact unreachable at that text position).
  Record the server-reported `prompt_n` as the truth and do not "correct" it to 512.

**Tokenizer cross-check.** The prompt file was generated with a Homebrew llama.cpp
build, not with `ea63b4d`. Compare the server-reported `prompt_n` for the three text
modes against 128 / 513 / 2048 and state in summary.md whether they match. If they do
not, the CSV still holds the truth and only the labels need adjusting — report the
discrepancy rather than working around it.

**Test the padded-window property.** The model card states the Whisper encoder runs
on the full padded 30 s mel window regardless of clip length. If `encoder_ms` and
`ttft_ms` for the 10 s clip come out close to the 30 s clip, that is a finding —
report it explicitly, because it means short-audio latency does not improve with
shorter input.

## MEMORY

- VRAM: `nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits` at 200 ms.
  Report peak minus the idle baseline reading.
- Host RSS: the `llama-server` process working set, same interval.
- Run with `-ngl 999` so all layers offload. If a variant does not fully offload,
  record the actual layer count on GPU and mark the row `partial offload`. A
  partially offloaded row is not comparable to a fully offloaded one.

## POWER

- `nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits` at 200 ms.
  Boundary = `GPU package (nvidia-smi)`.
- If HWiNFO64 or LibreHardwareMonitor is available, also log CPU package power and
  report a second total figure. If not, state clearly in summary.md that laptop wall
  power is higher than the reported figure.
- Measure a 60 s idle baseline under identical conditions before the first run and
  again after the last.
- `energy_j_per_1k_tok = (avg_power_w - idle_power_w) * decode_seconds / generated_tokens * 1000`

## CONDITIONS

- Plugged into AC. Windows power plan on Best Performance. Record the Armoury Crate
  profile used (Turbo or otherwise).
- Close background applications. Record GPU idle utilization before starting.
- `thermal_state = "sustained"` on all rows. Before the first measured run of each
  variant, generate continuously for 3 minutes so clocks settle. Record GPU
  temperature at the start and end of each variant.

## EXPECTED FIT

At 4096 context the KV cache costs roughly 0.6 GB (verify the head configuration from
the GGUF metadata rather than trusting this figure). With the 2.2 GB audio+vision
projector:

| Variant | Approx. total | 16 GB VRAM |
|---|---|---|
| BF16 | ~10.9 GB | fits |
| Q8_0 | ~7.1 GB | fits |
| Q6_K | ~6.1 GB | fits |
| Q5_K_M | ~5.7 GB | fits |
| Q4_K_M | ~5.3 GB | fits |

Every variant should fit here. If one does not, that is a real result — record it,
do not work around it by reducing context.

## N/A CELLS

Never write a bare `N/A`. Write `N/A (needs X.X GB, device has Y.Y GB usable)` or
`N/A (backend error: <verbatim message>)`. Compute the requirement as weights +
projector + KV cache at 4096 context so the cell stays quantitative.

## OUTPUT

Write `results.csv` with exactly these columns:

```
device_class, device_name, backend, llamacpp_commit, patch_applied, variant,
mmproj_variant, mode, prompt_tokens, image_tokens, audio_tokens, audio_seconds,
gen_tokens, run_idx, thermal_state, ttft_ms, encoder_ms, prefill_tps, decode_tps,
total_ms, peak_rss_gb, peak_vram_gb, avg_power_w, idle_power_w,
energy_j_per_1k_tok, notes
```

Set `device_class = "discrete-gpu-laptop"`, `backend = "CUDA"`.

Also write `summary.md` containing:
- the median table, one row per variant x mode
- the exact commands you ran
- every deviation from this protocol, listed explicitly
- an environment block: OS version, driver and CUDA version, CPU, GPU, RAM, power
  source, ambient conditions
- the artifact hashes and the llama.cpp commit

Three significant figures. Do not round aggressively. Report failures as failures —
a missing number is fine, a guessed number is not.
