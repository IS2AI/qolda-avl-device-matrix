# MANIFEST

Every file in this repository, with its sha256. Check them all with `./verify.sh`,
or directly:

```
shasum -a 256 -c <(awk -F'|' '/^\| `/ {gsub(/[` ]/,"",$2); gsub(/[` ]/,"",$5); print $5"  "$2}' MANIFEST.md)
```

Not included, by design:

- **The model files** (~19 GiB): the five GGUF variants and two mmproj files.
  They are the published `issai/Qolda-AVL-5B-GGUF` artifacts and their sha256
  values are recorded in `validation_report.md` and `macbook/file_manifest.json`.
  Each device's setup script downloads them.
- **`power.log`** (142 MB of raw `powermetrics` output from Device 2). The
  aggregated per-run figures it produced are in `macbook/raw_runs.jsonl` and
  `macbook/results.csv`.
- **The protocol inputs staged into device directories.** `prompts_text.txt` and
  the three media files are canonical in `protocol/` and copied into each device
  directory by its setup script, so they are stored once rather than four times.

| file | bytes | rows | sha256 | what it is |
|---|---:|---|---|---|
| `.gitignore` | 771 |  | `0addfe7bbae72548c2371c76d92d316350c20ebc78ac084124d1a754c8cab3c3` | Excludes model weights, llama.cpp builds, raw sampler logs, and the protocol inputs staged into device directories. |
| `LICENSE` | 11,358 |  | `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` | Apache License 2.0, verbatim canonical text. Covers the code: drivers, libraries, setup and run scripts, tools. |
| `NOTICE.md` | 3,033 |  | `17b1c052e1b60e6d772aa0d97d9cea78ad1e807089456d17325932a638bacc9d` | Licensing, copyright, and third-party terms for the llama.cpp patch, the FLEURS-derived audio, the Wikipedia-derived text, and bench_image.jpg. |
| `README.md` | 13,975 |  | `9ac526389e5daa6670455d7fa6b122ebb25237d2f15a02ee060294ef0661c155` | Entry point: devices, headline results, layout, what is and is not comparable, how to reproduce. |
| `REVIEW_REPLY.md` | 9,343 |  | `4e91c98b4531bc8c8221e2b14f45a5d957785d5e0a6ea59236e263679329f261` | Reply text for the review thread, Russian and English. |
| `cross_device_summary.md` | 48,655 |  | `15ea8f891b39521afeb26dc4000869f1defa1548c6bd896c1f10b281c8f7b001` | Cross-device comparison: measurement boundaries, comparable-metric tables, synthesis, limits. |
| `merged_results.csv` | 249,817 | 471 rows | `6c594d886bbc4b542f3f522a7de5b32e11c592253cfab69639b207c3055ee448` | All 471 measured rows from the three devices; the protocol's 26 columns plus power_boundary, Device 3's two extra columns, and device_id/source_file/source_row provenance. Rebuild with tools/merge_results.py. |
| `requirements.txt` | 352 |  | `1d8f438b114e33bdb29b66c95f2dac7cba72c0a9d083a24a5cf6ad983334a02c` | Python packages needed by Device 1's driver. Devices 2 and 3 use the standard library only. |
| `validation_report.md` | 38,499 |  | `deb4dca5d0b1b01ad3b4b7f290a445b698b16f3e67b04b8128cf7d83b762a616` | Identity and consistency checks across the three devices; coverage grid; deviation reconciliation. |
| `verify.sh` | 949 |  | `d25b9b463eb9985650a0e6d32a67abe8b3e0720a0d45940f4a3b4664dd81f415` | Checks every file against this manifest, re-derives merged_results.csv and round-trips it, confirms one commit across devices. |
| `tools/merge_results.py` | 3,364 |  | `503108b28cf8b8f929a19cffee4465cff478acc96e2e9c21b009b1bc7c99106b` | Builds merged_results.csv from the three device CSVs and round-trips every cell against its source. |
| `protocol/bench_audio_10s.wav` | 320,078 |  | `c00cefb4f2d1c942f02eedebbc21dee4ccbc90cd1b2e08a40f18f162cfa77d0c` | Fixed 10 s audio input, byte-identical on all three devices. |
| `protocol/bench_audio_30s.wav` | 960,078 |  | `94c91da6916aa32b9ba6cd5e602a7eb941c3b2b637f46a1744dff7a8602bbbc7` | Fixed 30 s audio input, byte-identical on all three devices. |
| `protocol/bench_image.jpg` | 359,881 |  | `d45840444cdef3c8d81eaa73c720f78e49fd3274c510fc49fc12665c43bb2330` | Fixed vision input, byte-identical on all three devices. |
| `protocol/fetch_source.py` | 970 |  | `be26543b8ca7d0e473b0cea3c0d5a5aba914e9925d16d85f10026f4d2b32953f` | Fetches the Kazakh source corpus. |
| `protocol/make_prompts.py` | 4,471 |  | `89dd729243a34e48f1d28f505a87fcbc7df7691cb7e045b6b0e3a04a8f07127b` | Builds prompts_text.txt from source_kk.txt at exact token counts. |
| `protocol/parse_prompts.py` | 1,010 |  | `db3c329526c397ecd4df8d8220c9cdd1574e82ce4c937841e9da751886efb554` | Reads prompts_text.txt back and checks token counts. |
| `protocol/prompts_text.txt` | 7,603 |  | `bb5c5cf054819d5775533e5fb8d2914196865351b1c5144fe7bdee35759dcc09` | Kazakh text prompts at 128 / 513 / 2048 tokens, byte-identical on all three devices. |
| `protocol/qwen3avl-support.patch` | 23,627 |  | `bb27de1efd5b546d74b834395570f49d5e017db872f0586a771edf59d0f89bf3` | Patch applied on top of llama.cpp ea63b4d on all three devices, with zero fuzz. |
| `protocol/source_kk.txt` | 351,641 |  | `d98bb5bd1e43ebde228300a0a3d1af7056cbca15b50f04e4235ac4c5fc89d1b5` | Kazakh source corpus the text prompts were cut from. |
| `protocol/device_briefs/prompt_1_windows_rtx4090.md` | 11,855 |  | `9250b75e6fde4aad14b1d01880102a0412b868f6bd822b5633574cf588d7be14` | The measurement brief Device 1 was run against. |
| `rtx/bench.py` | 17,675 |  | `7cf0204d95feb32f3dee643f4dc3c40720b76a2b1cb2e18cb5d9e4b12b96c764` | Device 1 driver. Standalone; writes results.csv directly, no aggregation step. |
| `rtx/results.csv` | 39,242 | 160 rows | `03d33a46f7cab78c7f4fc997d4131fea9e43611bee3b42c44d71b4672f03f036` | Device 1 raw results, 160 rows, 26-column protocol schema. |
| `rtx/run.ps1` | 1,393 |  | `6f32f72e521b080abee6fec9801a06fb74bfff7362116395348ce5c758ec007f` | Device 1 preflight and matrix run. |
| `rtx/setup.ps1` | 2,154 |  | `5366892c6a9a0c8fb97aba633565e6f760b898a31ee2c9dc67961abca3f6eec3` | Device 1 build and model download. PowerShell: this device ran on Windows. |
| `rtx/summary.md` | 21,480 |  | `082be49e8109cf29a442fbb1368926e8308bd10dd731a06a2d9916dc4d31dbb3` | Device 1 run report: environment, deviations, exact commands, per-cell notes. |
| `macbook/aggregate.py` | 2,536 |  | `88c3ab436b3dd69310fc03517a34b325af791d9165764e52d4961fbead27342a` | Device 2: reads results.csv and prints per-cell medians. |
| `macbook/artifact_provenance.md` | 9,353 |  | `e95e55d3405c04513699322fec54e78448fd9341fe3e60ca4e37655332e6fa8e` | Device 2 provenance for the fixed inputs and the model files. |
| `macbook/bench.py` | 11,392 |  | `e9f2183168287fcbd0b83712f5ad43d5c7bdaffb9bf6695a3d464b536a3b68ea` | Device 2 driver. Writes results.csv and raw_runs.jsonl. Aborts if powermetrics is not running. |
| `macbook/bench_lib.py` | 9,643 |  | `8deb14d3c9189d2132ff27572745bcba0eb7193b5c1ee6c4bc7f32c0e3c8796e` | Device 2 library: server launch, request bodies, generation settings, Kazakh instructions, power-log parsing, metric extraction. |
| `macbook/env.json` | 767 |  | `dd677abf849b637a9c76f9e37029c2ccdb755b3f520534c957a98534594a4e9f` | Device 2 environment record: OS, chip, toolchain, power state. |
| `macbook/file_manifest.json` | 1,233 |  | `eb41cad67af833b7290abd1f883acc1d4cf8c8797fe1f204d4d560824b97f8c0` | Device 2 model artifact sizes and sha256 prefixes. |
| `macbook/idle_baselines.json` | 76 |  | `a1b753937ff564e21f55d406bb980743ab9d44548998478abde676051f220c5c` | Device 2 idle power baselines, start and end of the matrix. |
| `macbook/idle_clean.json` | 36 |  | `2af84b6260904e34b0ae33829d7a2c532945872a6d91a6122033434a899e3a75` | Device 2 cleaned idle baseline actually used. |
| `macbook/raw_runs.jsonl` | 181,078 | 160 records | `41af8cd283d160fe0745b12a370cbc3d2b70f43814032b3564c4a50c88d511fa` | Device 2 per-run raw records behind every CSV row. |
| `macbook/results.csv` | 62,050 | 160 rows | `7cbe31a00e421f0e99e47553a6a07626b0fbb7b318e21d833d1e118f3fae0767` | Device 2 raw results, 160 rows, 26-column protocol schema. |
| `macbook/run.sh` | 1,598 |  | `c649e21dbbe84f2acf44c864e6dd299bf65faeee6481ef80bbfaeab347e7d7cd` | Device 2: starts powermetrics and caffeinate, runs the matrix, stops the sampler on exit. |
| `macbook/setup.sh` | 1,456 |  | `3ae43289e4c2222d495772fac1d52087207ff0d7faa11502e4b9e3d518020bcc` | Device 2 build, model download, and staging of the protocol inputs. |
| `macbook/summary.md` | 24,515 |  | `fbb77636dc79fa4f1d411f6d63267bbd5b131cbdf3f034519f3d8cd72f31cd68` | Device 2 run report: environment, deviations, exact commands, per-cell notes. |
| `one-plus/aggregate.py` | 3,368 |  | `7475cab6104eddbaf68b98f2cd08899c6a111f377db7ebb9ca7d1b2e986ccb07` | Device 3: reads results.csv and prints per-cell medians. |
| `one-plus/bench.py` | 27,207 |  | `fda431f7d045bf38e4631736c71f0ab97fcf31b083875decb7ff43405b645673` | Device 3 driver. Runs on the Mac, drives llama-server on the phone over wireless ADB. Writes results.csv and raw_runs.jsonl; resumable from raw_runs.jsonl. |
| `one-plus/bench_lib.py` | 25,141 |  | `60933450f93d1ee0c0b093b52f4820cbd7e7cee8b5b52aa60122db714844bb18` | Device 3 library: adb plumbing, on-device server launch, sampling, request bodies, generation settings, metric extraction. |
| `one-plus/calibrate_power.py` | 5,664 |  | `7303546e433c99c305d9597da8ea4f9149a60ef8c70895cc481723b7db4283c0` | Device 3 power sampler calibration against the battery register. |
| `one-plus/env.json` | 3,091 |  | `f63c9d040873023f700cfb220b4f81c2e0c2c0f7fdfd17dd5a4c84f2ceb9b8ac` | Device 3 environment record, including per-location idle power and the superseded 0.433 W baseline. |
| `one-plus/power_calc.py` | 4,109 |  | `39a9b3677641f640d17d2fad35f0a2166ee6c4225940a72909ddbe25e2d053a9` | Device 3 battery power derivation (mA x mV) and idle subtraction. |
| `one-plus/raw_runs.jsonl` | 533,947 | 151 records | `b5402adfca333a9ce93dbb685142489d7fcd0b7469beeccf04111295ca9afa09` | Device 3 per-run raw records behind every CSV row; also the resume log. |
| `one-plus/raw_runs_1hz_registercal.jsonl` | 17,429 | 8 records | `55711f4b4da8097c7dec5b976dfe89d6c4713e1aeff8975c65f61da523dd0b1b` | Device 3 1 Hz register-calibration run validating the power sampler. |
| `one-plus/results.csv` | 106,879 | 151 rows | `a729fb19436b4d1b01d1097310d2aae45541f68a35383897dd36761e2f4e65cc` | Device 3 raw results, 151 rows, protocol schema plus avg_power_w_raw and power_samples_used. |
| `one-plus/run.sh` | 2,223 |  | `10b8ccf60cc94e1d068ce0e545762f8ef695c30e1e024f5d7e8cfb0278cc4f63` | Device 3 preflight (unplugged, reachable, staged), calibration, token census, then the matrix. |
| `one-plus/setup.sh` | 2,876 |  | `80aae6dbefffbeb3f8090ca58813f088d1f01975c5b3ee75dbb88467fc176edc` | Device 3 Android build, model download, and staging to /data/local/tmp/qolda. |
| `one-plus/summary.md` | 39,213 |  | `b47343bd0be32f55f6ea4aab884a49356fed75f5c859853479dd9a29ba323b4c` | Device 3 run report: environment, deviations D1 to D15, exact commands, per-cell notes. |
| `one-plus/token_census.json` | 1,090 |  | `3edbfbffb79521f8520aa4fa11875aa20d39984ced9602092268b86dff03e145` | Device 3 token census output, including the 12-token chat-template overhead. |
| `one-plus/token_census.py` | 4,681 |  | `0f12e3ada2d565f1a2409d2348ff0e58520584243ea4c97e0e88ef87e216a770` | Device 3: derives image and audio token counts from the server's prompt_n. |
