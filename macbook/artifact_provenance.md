# Prompt generation summary

## Source text

Kazakh Wikipedia (CC BY-SA), retrieved 2026-08-26 via the `kk.wikipedia.org`
API (`action=query`, `prop=extracts`, `explaintext=1`).

Articles used:

- Қазақстан
- Абай Құнанбайұлы
- Астана
- Алматы
- Қазақ тілі
- Қазақ хандығы
- Мұхтар Әуезов
- Тұран

Total: 25,461 words, written to `source_kk.txt`.

## Tokenizer

`llama-tokenize` from the Homebrew `llama.cpp` build (0.3.0), used in
vocab-only mode against `models/Q4_K_M/Qolda-AVL-5B-Q4_K_M.gguf`
(`issai/Qolda-AVL-5B-GGUF`). Vocab is identical across all five
quantizations, so the smallest was used to build the tokenizer input.
Used only for prompt generation — the benchmark itself runs the patched
build at `ea63b4d`.

## Prompt construction

`make_prompts.py` binary-searches a prefix of the source text (word-level,
then character-level at the boundary word) so that
`prefix + INSTRUCTION` tokenizes (no BOS) to the target length. The fixed
instruction suffix (110 tokens) turns each prompt into an instruction-shaped
query instead of a raw Wikipedia dump — a fairer prefill workload — and is
kept even though `ignore_eos` means it no longer needs to anchor generation
length to 256 tokens.

## Results

```
Instruction suffix: 110 tokens
target   128 -> actual   128  [OK]
target   512 -> actual   513  [OFF BY 1]
target  2048 -> actual  2048  [OK]
```

The 512 target lands one token high. Diagnosed as a genuine BPE merge
artifact, not a script bug: at word 81 of the source text, a leftover
citation-style numeral (`"(7"`) sits exactly on the boundary. Appending `"("`
alone holds the count at 511 tokens; appending the following `"7"` jumps
straight to 513 — one character addition merges into two extra tokens, so
512 exact is unreachable at that text position. Accepted as-is since the
same prompt file is used across all three benchmark devices.

Target was 512; the reachable value at this text position is 513. **The
paper's column for this row should be labeled 513, not 512** — `bench.py`
records `prompt_n` from the server response, so that measured value is the
source of truth, not the target used to generate the prompt.

## Instruction/content ratio

The instruction suffix is fixed at 110 tokens across all three prompts. For
the 128-token prompt this means 110 tokens are fixed instruction and only
18 tokens are source-text content. Prefill throughput itself is unaffected
(128 tokens is 128 tokens regardless of the instruction/content split), but
**the 128-token row should not be read as representative of short user
queries** — it is a short prefill with a proportionally large fixed
instruction, not a short instruction. A shorter suffix could fix this for
the 128 case specifically, but would break the constant-suffix property
across prompt lengths; left as-is and documented here instead.

## Cross-check pending (Windows run)

Token counts above come from the Homebrew `llama.cpp` build (0.3.0); the
benchmark itself runs the patched build at `ea63b4d`. The model card states
the tokenizer round-trips exactly against HF, so divergence is unlikely,
but this is unverified. On the Windows run, compare the server-reported
`prompt_n` against 128 / 513 / 2048. If they match, record that here as a
verified cross-check; if they don't, the CSV still records the true value
and only the labels need adjusting.

## Output

`prompts_text.txt` — 3 prompts, delimited by opening markers only (no
closing markers): `<<<PROMPT_128>>>`, `<<<PROMPT_512>>>`,
`<<<PROMPT_2048>>>`. Each prompt runs until the next delimiter or EOF.

sha256: `bb5c5cf054819d5775533e5fb8d2914196865351b1c5144fe7bdee35759dcc09`

# Audio benchmark artifacts

## Source

FLEURS `kk_kz` (Google, CC-BY), downloaded 2026-08-26 from
`google/fleurs` on Hugging Face (`refs/convert/parquet` branch, `test` and
`validation` splits, 856 + 369 rows).

FLEURS provides no speaker-ID field (only `gender`), so concatenating
separate clips could not be verified as single-speaker. Before choosing a
source, checked clip-length distribution instead: 21 clips across the two
splits are already ≥30 s on their own (test: 15, validation: 6), so **no
splicing was needed** — a single clip covers the full 30 s natively, which
also satisfies the single-speaker requirement by construction.

Common Voice Kazakh was ruled out: as of Oct 2025 Mozilla moved Common
Voice off Hugging Face to "Mozilla Data Collective"; the HF mirror
(`mozilla-foundation/common_voice_17_0`) now contains only `.gitattributes`
and `README.md`, no audio. ISSAI KSC/KSC2 was not used because no local
path was provided for this run.

## Clip selected

`test` split, `id=1983`, duration 34.44 s, native 16 kHz mono
`pcm_f32le` WAV, gender field = 1.

Raw transcription:
> Өркениет сөзі латынның «civilis» сөзінен шыққан, азаматтық деген
> мағынаны білдіретін, ол азамат деген мағынаны білдіретін, латынша
> «civis» сөзімен байланысты, ал қала немесе қала-мемлекет деген мағынаны
> білдіретін «civitas» сөзі де бар, сонымен бірге бұл белгілі бір деңгейде
> қоғамның көлемін анықтайды.

Chosen over the other 20 candidates ≥30 s for being comfortably longer
than 30 s (so the cut lands mid-speech, not at the clip's natural end) and
for prose content over digit-heavy passages.

`ffmpeg silencedetect` (noise=-35dB, d=0.6s) on the source clip: leading
silence 0–1.88 s (normal recording lead-in), internal pauses all ≤1.2 s,
and the only long gap (3.35 s) starts at 31.09 s — after the 30 s cutoff,
so it does not appear in either output file. The first 30 s is therefore
continuous speech with only ordinary sentence-level pauses.

## Processing

```
ffmpeg -i source_raw.wav -ac 1 -ar 16000 -ss 0 -t 30 -c:a pcm_s16le bench_audio_30s.wav
ffmpeg -i bench_audio_30s.wav -ss 0 -t 10 -c:a pcm_s16le bench_audio_10s.wav
```

No splicing, no loudness normalization, no denoising, no silence trimming,
no fades. `source_raw.wav` was float32 PCM from the parquet's embedded
audio; `-c:a pcm_s16le` on output is the only format conversion applied.

Verified `bench_audio_10s.wav`'s PCM data (`data` chunk payload) is a
byte-for-byte exact prefix of `bench_audio_30s.wav`'s PCM data — the 10 s
file is a true prefix of the 30 s file, not an independent cut from the
source.

## Output

| file | format | duration | sha256 |
|---|---|---|---|
| `bench_audio_30s.wav` | 16 kHz mono PCM s16le | 30.000000 s | `94c91da6916aa32b9ba6cd5e602a7eb941c3b2b637f46a1744dff7a8602bbbc7` |
| `bench_audio_10s.wav` | 16 kHz mono PCM s16le | 10.000000 s | `c00cefb4f2d1c942f02eedebbc21dee4ccbc90cd1b2e08a40f18f162cfa77d0c` |

## Frame count verification

Raw output of the `wave`-module check (verbatim):

```
bench_audio_30s.wav channels 1 rate 16000 sampwidth 2 frames 480000 OK
bench_audio_10s.wav channels 1 rate 16000 sampwidth 2 frames 160000 OK
```

480000 = 30 s × 16000 Hz and 160000 = 10 s × 16000 Hz exactly, at 1 channel
and 2 bytes/sample. No partial frames, no resampling drift.

## Conversion sanity check

The source was float32 PCM extracted from the parquet blob and converted to
s16le, so the output was checked numerically for conversion damage
(wrong endianness, wrong scaling, clipping) that format checks alone would
not catch:

```
bench_audio_30s.wav peak 6859 peak_dBFS -13.58 rms_dBFS -30.36 clipped_samples 0 zero_frac 0.0272
bench_audio_10s.wav peak 6859 peak_dBFS -13.58 rms_dBFS -30.35 clipped_samples 0 zero_frac 0.0509
```

Clean: zero clipped samples, RMS around -30 dBFS (well above the ~-45 dBFS
near-silence threshold), and a low zero fraction. Peak is -13.58 dBFS,
marginally quieter than a typical -12 to -0.5 dBFS band — this is an
unnormalized corpus recording and no loudness normalization was applied by
design, so the modest level is expected rather than a conversion fault. Both
files share the same peak sample value (6859), consistent with the loudest
moment falling inside the first 10 s.

`audio_waveform.png` (both files stacked) shows clear syllable-level
amplitude envelope variation rather than a constant band or flat line, with
silence gaps at the positions `silencedetect` reported, and the 10 s panel
visibly matching the opening 10 s of the 30 s panel.

## Licensing and reviewer notes

**Attribution.** FLEURS is CC-BY and requires attribution. The paper must
cite Google's FLEURS dataset, identifying the split (`test`) and the clip ID
(`1983`) used for these artifacts.

**Test-split use.** Using a clip from the `test` split is acceptable here
because this is a latency measurement run with `ignore_eos` and no
transcription quality is scored, so test-set contamination does not apply.

**Leading silence.** The clip carries 1.88 s of leading silence, so the 10 s
file contains roughly 8.1 s of speech and the 30 s file roughly 28.1 s. This
does not affect the measurement — audio token count is a function of sample
count rather than content, and the Whisper encoder pads to a full 30 s window
regardless — but it is recorded here so a reviewer inspecting the artifact
can see it was noticed rather than missed.
