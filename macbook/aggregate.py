#!/usr/bin/env python3
"""Median + min-max aggregation over results.csv, 3 significant figures."""
import csv, statistics as st, sys
from collections import OrderedDict

def sig3(x):
    return "" if x is None else f"{float(f'{x:.3g}'):g}"

def fnum(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None

MET = ["ttft_ms", "prefill_tps", "decode_tps", "peak_rss_gb", "avg_power_w",
       "energy_j_per_1k_tok"]

def load(path="results.csv"):
    return list(csv.DictReader(open(path)))

def group(rows):
    g = OrderedDict()
    for r in rows:
        k = (r["variant"], r["mmproj_variant"], r["mode"])
        g.setdefault(k, []).append(r)
    return g

def summarize(rows):
    g = group(rows)
    out = []
    for (variant, mmv, mode), rs in g.items():
        rec = dict(variant=variant, mmproj_variant=mmv, mode=mode, n=len(rs))
        rec["prompt_tokens"] = rs[0].get("prompt_tokens", "")
        rec["image_tokens"]  = rs[0].get("image_tokens", "")
        rec["audio_tokens"]  = rs[0].get("audio_tokens", "")
        failed = [r for r in rs if "N/A" in r.get("notes", "") or "RUN FAILED" in r.get("notes", "")]
        rec["failed"] = len(failed)
        for m in MET:
            vals = [fnum(r[m]) for r in rs if fnum(r[m]) is not None]
            if vals:
                rec[m] = sig3(st.median(vals))
                rec[m + "_range"] = f"{sig3(min(vals))}–{sig3(max(vals))}"
                rec[m + "_vals"] = vals
            else:
                rec[m] = ""; rec[m + "_range"] = ""; rec[m + "_vals"] = []
        flagged = [r["run_idx"] for r in rs if "HEAVY" in r.get("notes", "")]
        rec["flagged_runs"] = flagged
        out.append(rec)
    return out

def md_table(recs):
    hdr = ("| variant | mmproj | mode | prompt_tok | ttft_ms (median) | ttft range | "
           "prefill_tps | decode_tps | peak_rss_gb | avg_power_w | energy_J/1k_tok | n |")
    sep = "|" + "---|" * 12
    lines = [hdr, sep]
    for r in recs:
        lines.append("| " + " | ".join([
            r["variant"], r["mmproj_variant"], r["mode"], str(r["prompt_tokens"]),
            r["ttft_ms"], r["ttft_ms_range"], r["prefill_tps"],
            r["decode_tps"], r["peak_rss_gb"], r["avg_power_w"],
            r["energy_j_per_1k_tok"], str(r["n"])]) + " |")
    return "\n".join(lines)

if __name__ == "__main__":
    rows = load(sys.argv[1] if len(sys.argv) > 1 else "results.csv")
    recs = summarize(rows)
    print(md_table(recs))
    print(f"\ncells: {len(recs)}  rows: {len(rows)}")
