#!/usr/bin/env python3
"""Median + min-max aggregation over results.csv, 3 significant figures.

One row per variant x mmproj_variant x mode x thermal_state, per the protocol's
output spec. Outliers are flagged and retained, never discarded.
"""
import csv, statistics as st, sys
from collections import OrderedDict

MET = ["ttft_ms", "prefill_tps", "decode_tps", "peak_rss_gb", "avg_power_w",
       "energy_j_per_1k_tok"]


def sig3(x):
    return "" if x is None else f"{float(f'{x:.3g}'):g}"


def fnum(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def load(path="results.csv"):
    return list(csv.DictReader(open(path)))


def summarize(rows):
    g = OrderedDict()
    for r in rows:
        k = (r["variant"], r["mmproj_variant"], r["mode"], r["thermal_state"])
        g.setdefault(k, []).append(r)

    out = []
    for (variant, mmv, mode, thermal), rs in g.items():
        rec = dict(variant=variant, mmproj_variant=mmv, mode=mode,
                   thermal_state=thermal, n=len(rs))
        rec["prompt_tokens"] = rs[0].get("prompt_tokens", "")
        rec["image_tokens"] = rs[0].get("image_tokens", "")
        rec["audio_tokens"] = rs[0].get("audio_tokens", "")
        rec["failed"] = sum(1 for r in rs if "RUN FAILED" in r.get("notes", ""))
        notes = []
        for m in MET:
            vals = [fnum(r[m]) for r in rs if fnum(r[m]) is not None]
            if vals:
                med = st.median(vals)
                rec[m] = sig3(med)
                rec[m + "_range"] = f"{sig3(min(vals))}–{sig3(max(vals))}"
                # Flag (do not drop) any value more than 25% off the median.
                if med:
                    odd = [(r["run_idx"], v) for r, v in
                           zip([x for x in rs if fnum(x[m]) is not None], vals)
                           if abs(v - med) / abs(med) > 0.25]
                    if odd:
                        notes.append(f"{m} outliers retained: " +
                                     ", ".join(f"run{i}={sig3(v)}" for i, v in odd))
            else:
                rec[m] = rec[m + "_range"] = ""
        rec["outlier_notes"] = "; ".join(notes)
        out.append(rec)
    return out


def md_table(recs):
    hdr = ("| variant | mmproj | mode | thermal | prompt_tok | ttft_ms | ttft range | "
           "prefill_tps | decode_tps | decode range | peak_rss_gb | avg_power_w | "
           "energy_J/1k_tok | n |")
    sep = "|" + "---|" * 14
    lines = [hdr, sep]
    for r in recs:
        lines.append("| " + " | ".join([
            r["variant"], r["mmproj_variant"], r["mode"], r["thermal_state"],
            str(r["prompt_tokens"]), r["ttft_ms"], r["ttft_ms_range"],
            r["prefill_tps"], r["decode_tps"], r["decode_tps_range"],
            r["peak_rss_gb"], r["avg_power_w"], r["energy_j_per_1k_tok"],
            str(r["n"])]) + " |")
    return "\n".join(lines)


if __name__ == "__main__":
    rows = load(sys.argv[1] if len(sys.argv) > 1 else "results.csv")
    recs = summarize(rows)
    print(md_table(recs))
    notes = [f"- {r['variant']}/{r['mode']}/{r['thermal_state']}: {r['outlier_notes']}"
             for r in recs if r.get("outlier_notes")]
    if notes:
        print("\nOutliers (retained, not discarded):")
        print("\n".join(notes))
    print(f"\ncells: {len(recs)}  rows: {len(rows)}")
