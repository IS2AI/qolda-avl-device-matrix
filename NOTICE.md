# NOTICE

Copyright 2026 Institute of Smart Systems and Artificial Intelligence (ISSAI),
Nazarbayev University.

This repository is released under two licenses.

| what | license | file |
|---|---|---|
| Code: the benchmark drivers, libraries, setup and run scripts, and tools | Apache License 2.0 | `LICENSE` |
| Results and reports: the device CSVs, `merged_results.csv`, the raw run records, the summaries and the cross-device reports | CC-BY-4.0 | `LICENSE-DATA` |

Third-party material carries its own terms and is **not** relicensed by either
of the above.

## Third-party material

### `protocol/qwen3avl-support.patch`

A patch against [llama.cpp](https://github.com/ggml-org/llama.cpp) at commit
`ea63b4d32ea1b66bdbe369be7f9443f6c00f8b31`. It is a derivative work of
llama.cpp and is subject to llama.cpp's MIT license. Copyright of the
surrounding code remains with the llama.cpp authors and contributors.

### `protocol/bench_audio_10s.wav`, `protocol/bench_audio_30s.wav`

Derived from **FLEURS** (`google/fleurs`, configuration `kk_kz`, `test` split,
clip ID `1983`), downloaded 2026-08-26 from the `refs/convert/parquet` branch on
Hugging Face. FLEURS is published by Google under **CC-BY** and requires
attribution.

The files here are processed: converted to mono 16 kHz PCM s16le and truncated
to the first 10 s and 30 s of the source clip with no fades and no loudness
normalization. Processing details are in `macbook/artifact_provenance.md`.

> Conneau, A., Ma, M., Khanuja, S., Zhang, Y., Axelrod, V., Dalmia, S.,
> Riesa, J., Rivera, C., Bapna, A. *FLEURS: Few-shot Learning Evaluation of
> Universal Representations of Speech.* 2022.

### `protocol/source_kk.txt`, `protocol/prompts_text.txt`

Text retrieved 2026-08-26 from Kazakh Wikipedia (`kk.wikipedia.org`).
**Wikipedia article text is licensed CC BY-SA**, which is a share-alike license
and is therefore *not* covered by this repository's CC-BY-4.0 grant. Reuse of
these two files, and of anything derived from them, must follow CC BY-SA and
attribute Kazakh Wikipedia.

`prompts_text.txt` is a word-level prefix of `source_kk.txt` cut to exact token
counts by `protocol/make_prompts.py`, so it inherits the same terms.

### `protocol/bench_image.jpg`

**Provenance is not recorded.** The file is identified throughout this
repository by its sha256
(`d45840444cdef3c8d81eaa73c720f78e49fd3274c510fc49fc12665c43bb2330`) and was
verified byte-identical on all three devices, but no source, author or license
was captured for it at measurement time, and none is stated in any device's
summary or provenance record.

No license is asserted over this file here. Anyone redistributing this
repository should establish its origin first, or replace it with an image of
known provenance and re-run the four vision cells.

## Not included in this repository

The model weights (`issai/Qolda-AVL-5B-GGUF`) and the llama.cpp source tree are
downloaded by each device's setup script and are governed by their own licenses
at their source.
