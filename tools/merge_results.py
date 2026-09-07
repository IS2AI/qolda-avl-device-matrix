#!/usr/bin/env python3
"""Concatenate the three device CSVs into merged_results.csv.

Adds nothing that is not already in a device CSV. The only new columns are
`power_boundary` (a constant per device, stating which hardware that device's
power figures enclose) and `device_id` / `source_file` / `source_row`, which
point every merged row back at the exact line it came from.

Refuses to run if a device CSV deviates from the protocol's 26-column schema.
"""
import csv, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

COLS26 = [
    "device_class", "device_name", "backend", "llamacpp_commit", "patch_applied",
    "variant", "mmproj_variant", "mode", "prompt_tokens", "image_tokens",
    "audio_tokens", "audio_seconds", "gen_tokens", "run_idx", "thermal_state",
    "ttft_ms", "encoder_ms", "prefill_tps", "decode_tps", "total_ms",
    "peak_rss_gb", "peak_vram_gb", "avg_power_w", "idle_power_w",
    "energy_j_per_1k_tok", "notes",
]
EXTRA = ["avg_power_w_raw", "power_samples_used"]   # Device 3 only

SOURCES = [
    ("D1", "rtx/results.csv",
     "gpu-package (nvidia-smi power.draw; CPU package not captured)"),
    ("D2", "macbook/results.csv",
     "soc-package (powermetrics CPU Power + GPU Power; excludes display, DRAM, ANE)"),
    ("D3", "one-plus/results.csv",
     "whole-device battery (BatteryManager mA x mV)"),
]

OUT_COLS = COLS26 + ["power_boundary"] + EXTRA + ["device_id", "source_file", "source_row"]


def main():
    rows, counts = [], []
    for dev, rel, boundary in SOURCES:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            src = list(csv.DictReader(f))
        header = list(src[0].keys())
        if header[:26] != COLS26:
            sys.exit(f"FATAL: {rel} first 26 columns deviate from the protocol schema")
        if header[26:] not in ([], EXTRA):
            sys.exit(f"FATAL: {rel} has unexpected extra columns {header[26:]}")
        for i, r in enumerate(src, 1):
            out = {c: r.get(c, "") for c in COLS26}
            out["power_boundary"] = boundary
            for c in EXTRA:
                out[c] = r.get(c, "")
            out["device_id"], out["source_file"], out["source_row"] = dev, rel, i
            rows.append(out)
        counts.append((dev, rel, len(src), len(header)))

    dest = os.path.join(ROOT, "merged_results.csv")
    with open(dest, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS)
        w.writeheader()
        w.writerows(rows)

    for dev, rel, n, nc in counts:
        print(f"{dev}  {rel:24s} rows={n:4d} cols={nc}")
    print(f"->  merged_results.csv    rows={len(rows)} cols={len(OUT_COLS)}")

    # Round-trip: every merged cell must equal the source cell it came from.
    src_cache = {rel: list(csv.DictReader(open(os.path.join(ROOT, rel), encoding="utf-8")))
                 for _, rel, _ in SOURCES}
    bad = cells = 0
    for m in rows:
        orig = src_cache[m["source_file"]][m["source_row"] - 1]
        for c, v in orig.items():
            cells += 1
            if m[c] != v:
                bad += 1
                print(f"MISMATCH {m['source_file']}:{m['source_row']} {c} "
                      f"{v!r} != {m[c]!r}")
    print(f"round-trip: {cells} cells compared, {bad} mismatches")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
