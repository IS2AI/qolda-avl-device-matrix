#!/usr/bin/env python3
"""Qolda-AVL-5B deployment benchmark - Device 2: MacBook Pro / Apple M4 Pro (Metal)."""
import csv, json, os, subprocess, sys, time
import bench_lib as B

COMMIT   = "ea63b4d32ea1b66bdbe369be7f9443f6c00f8b31"
DEVCLASS = "unified-memory-laptop"
DEVNAME  = "MacBook Pro / Apple M4 Pro 14-core / 24 GB unified"
BACKEND  = "Metal"
PATCHED  = "yes"

MMPROJ_AV = "models/mmproj/mmproj-Qolda-AVL-5B-F16.gguf"
MMPROJ_V  = "models/mmproj/mmproj-Qolda-AVL-5B-vision-only-F16.gguf"

VARIANTS = [
    ("BF16",   "models/BF16/Qolda-AVL-5B-BF16.gguf"),
    ("Q8_0",   "models/Q8_0/Qolda-AVL-5B-Q8_0.gguf"),
    ("Q6_K",   "models/Q6_K/Qolda-AVL-5B-Q6_K.gguf"),
    ("Q5_K_M", "models/Q5_K_M/Qolda-AVL-5B-Q5_K_M.gguf"),
    ("Q4_K_M", "models/Q4_K_M/Qolda-AVL-5B-Q4_K_M.gguf"),
]
MODES = ["text-128", "text-512", "text-2048", "vision", "audio-30s", "audio-10s"]

# Token counts measured once with llama-tokenize / llama-mtmd-cli -v (see summary.md).
MODE_TOK = {
    "text-128":  dict(image_tokens="", audio_tokens="", audio_seconds=""),
    "text-512":  dict(image_tokens="", audio_tokens="", audio_seconds=""),
    "text-2048": dict(image_tokens="", audio_tokens="", audio_seconds=""),
    "vision":    dict(image_tokens=1024, audio_tokens="", audio_seconds=""),
    "audio-30s": dict(image_tokens="", audio_tokens=1500, audio_seconds="30.0"),
    "audio-10s": dict(image_tokens="", audio_tokens=500,  audio_seconds="10.0"),
}

COLUMNS = ["device_class","device_name","backend","llamacpp_commit","patch_applied",
           "variant","mmproj_variant","mode","prompt_tokens","image_tokens",
           "audio_tokens","audio_seconds","gen_tokens","run_idx","thermal_state",
           "ttft_ms","encoder_ms","prefill_tps","decode_tps","total_ms",
           "peak_rss_gb","peak_vram_gb","avg_power_w","idle_power_w",
           "energy_j_per_1k_tok","notes"]

CSV_PATH = "results.csv"
GIB = 1024 ** 3


def sig3(x):
    if x is None:
        return ""
    if x == 0:
        return "0.00"
    from decimal import Decimal
    return f"{float(f'{x:.3g}'):g}"


def parse_power_tail(nbytes=4_000_000):
    p = B.POWER_LOG
    if not os.path.exists(p):
        return []
    size = os.path.getsize(p)
    with open(p, "rb") as f:
        f.seek(max(0, size - nbytes))
        txt = f.read().decode("utf-8", "replace")
    tmp = "/tmp/_pm_tail.txt"
    open(tmp, "w").write(txt)
    return B.parse_power_log(tmp)


class Bench:
    def __init__(self, idle_w):
        self.idle_w = idle_w
        self.rows = []
        new = not os.path.exists(CSV_PATH)
        self.fh = open(CSV_PATH, "a", newline="")
        self.w = csv.DictWriter(self.fh, fieldnames=COLUMNS)
        if new:
            self.w.writeheader(); self.fh.flush()

    def emit(self, row):
        self.w.writerow(row); self.fh.flush(); self.rows.append(row)

    def measure(self, srv, variant, mmproj_variant, mode, run_idx, prompts,
                thermal="sustained", extra_notes=""):
        ep, body = B.build_body(mode, prompts)
        vm0 = B.vm_stat()
        sampler = B.MemSampler(srv.proc.pid, 0.2); sampler.start()
        t0 = time.time()
        err = None
        try:
            r = B.stream_request(ep, body, timeout=3600)
        except Exception as e:
            err = e; r = None
        t1 = time.time()
        peak_kb = sampler.stop()
        vm1 = B.vm_stat()
        dv = B.vm_delta(vm0, vm1)

        notes = [n for n in [extra_notes] if n]
        notes.append("mmap=off")
        notes.append("encoder_ms folded into ttft_ms (llama-server does not report it)")

        if err is not None:
            notes.append(f"RUN FAILED: {type(err).__name__}: {str(err)[:200]}")
            row = self.base(variant, mmproj_variant, mode, run_idx, thermal)
            row.update(notes="; ".join(notes))
            self.emit(row); return row

        tt = r["timings"] or {}
        gen = tt.get("predicted_n") or r["stream_chunks"]
        ttft = (r["t_first"] - r["t_send"]) * 1000 if r["t_first"] else None
        dec_s = (r["t_last"] - r["t_first"]) if (r["t_first"] and r["t_last"]) else None
        decode_tps = ((gen - 1) / dec_s) if (dec_s and dec_s > 0 and gen > 1) else None
        prompt_n = tt.get("prompt_n"); prompt_ms = tt.get("prompt_ms")
        prefill_tps = (prompt_n / prompt_ms * 1000.0) if (prompt_n and prompt_ms) else None

        samples = parse_power_tail()
        avg_w = B.mean_power_in_window(samples, t0, t1)
        energy = None
        if avg_w is not None and dec_s and gen:
            energy = max(avg_w - self.idle_w, 0.0) * dec_s / gen * 1000.0

        # vm_stat is system-wide, not per-process: small deltas are ordinary OS
        # background activity. Always record them; only call a row invalid when the
        # volume is large enough to plausibly have touched this process.
        swi, swo = dv.get("Swapins", 0), dv.get("Swapouts", 0)
        cmp_ = dv.get("Compressions", 0)
        if swi or swo or cmp_:
            notes.append(f"vm_stat delta (system-wide) swapin={swi} swapout={swo} compress={cmp_}")
        if swo > 1000 or swi > 1000 or cmp_ > 1000:
            notes.append("SWAP/COMPRESSION HEAVY - treat throughput for this row as invalid")
        if gen != 256:
            notes.append(f"gen_tokens={gen} != 256")
        if avg_w is None:
            notes.append("no powermetrics samples in window")

        row = self.base(variant, mmproj_variant, mode, run_idx, thermal)
        row.update(
            prompt_tokens=prompt_n if prompt_n is not None else "",
            gen_tokens=gen,
            ttft_ms=sig3(ttft), encoder_ms="",
            prefill_tps=sig3(prefill_tps), decode_tps=sig3(decode_tps),
            total_ms=sig3((r["t_end"] - r["t_send"]) * 1000),
            peak_rss_gb=sig3(peak_kb * 1024 / GIB) if peak_kb else "",
            avg_power_w=sig3(avg_w), idle_power_w=sig3(self.idle_w),
            energy_j_per_1k_tok=sig3(energy),
            notes="; ".join(notes),
        )
        row["_raw"] = dict(prompt_n=prompt_n, prompt_ms=prompt_ms,
                           predicted_n=tt.get("predicted_n"),
                           predicted_ms=tt.get("predicted_ms"),
                           vm_delta=dv, t0=t0, t1=t1)
        self.emit({k: row.get(k, "") for k in COLUMNS})
        return row

    def base(self, variant, mmproj_variant, mode, run_idx, thermal):
        d = dict.fromkeys(COLUMNS, "")
        d.update(device_class=DEVCLASS, device_name=DEVNAME, backend=BACKEND,
                 llamacpp_commit=COMMIT, patch_applied=PATCHED,
                 variant=variant, mmproj_variant=mmproj_variant, mode=mode,
                 run_idx=run_idx, thermal_state=thermal,
                 peak_vram_gb="unified (no discrete VRAM)")
        d.update(MODE_TOK[mode])
        return d


KV_GIB = 576 / 1024.0          # verified from GGUF metadata: 36L x 8kv x 128d x 2 x 4096 x 2B
USABLE_GIB = 24 * 1000**3 / GIB  # 24 GB unified, reported as GiB


def req_gib(model_path, mmproj_path):
    w = os.path.getsize(model_path) / GIB
    m = os.path.getsize(mmproj_path) / GIB if mmproj_path else 0.0
    return w + m + KV_GIB


def idle_baseline(seconds=60, label="idle"):
    print(f"[{label}] measuring {seconds}s idle power baseline ...", flush=True)
    t0 = time.time(); time.sleep(seconds); t1 = time.time()
    s = parse_power_tail()
    w = B.mean_power_in_window(s, t0, t1)
    print(f"[{label}] idle power = {w} W  ({len(s)} samples parsed)", flush=True)
    return w, t0, t1


def thermal_soak(prompts, seconds=180):
    print(f"  thermal soak: generating continuously for {seconds}s ...", flush=True)
    ep, body = B.build_body("text-512", prompts)
    t0 = time.time(); n = 0
    while time.time() - t0 < seconds:
        try:
            B.stream_request(ep, body, timeout=600); n += 1
        except Exception as e:
            print(f"    soak request failed: {e}"); break
    print(f"  soak done ({n} requests, {time.time()-t0:.0f}s)", flush=True)


def run_cell(bench, srv, variant, mmproj_variant, mode, prompts, reps=5, thermal="sustained"):
    ep, body = B.build_body(mode, prompts)
    for i in range(3):                      # discarded warm-ups
        try:
            B.stream_request(ep, body, timeout=1800)
        except Exception as e:
            print(f"    warmup {i} failed: {e}", flush=True)
    out = []
    for r in range(1, reps + 1):
        row = bench.measure(srv, variant, mmproj_variant, mode, r, prompts, thermal)
        out.append(row)
        print(f"    {variant:7} {mmproj_variant:13} {mode:10} run{r} "
              f"ttft={row.get('ttft_ms'):>8} dec={row.get('decode_tps'):>6} "
              f"pf={row.get('prefill_tps'):>7} rss={row.get('peak_rss_gb'):>6} "
              f"pw={row.get('avg_power_w'):>6}", flush=True)
        with open("raw_runs.jsonl", "a") as f:
            f.write(json.dumps({k: v for k, v in row.items()}, default=str) + "\n")
    return out


def do_variant(bench, variant, model, mmproj, mmproj_variant, modes, prompts,
               thermal="sustained", soak=True):
    log = f"logs/server_{variant}_{mmproj_variant}.log"
    os.makedirs("logs", exist_ok=True)
    srv = B.Server(model, mmproj, log)
    print(f"\n=== {variant} / mmproj={mmproj_variant} ===", flush=True)
    try:
        t = srv.start()
        print(f"  server ready in {t:.1f}s", flush=True)
    except Exception as e:
        msg = str(e)[:400].replace("\n", " | ")
        need = req_gib(model, mmproj)
        for mode in modes:
            for r in range(1, 6):
                row = bench.base(variant, mmproj_variant, mode, r, thermal)
                row["notes"] = (f"N/A (backend error: {msg}); "
                                f"requirement = weights+projector+KV@4096 = {need:.2f} GiB, "
                                f"device has {USABLE_GIB:.2f} GiB usable")
                bench.emit({k: row.get(k, "") for k in COLUMNS})
        print(f"  !! SERVER FAILED: {msg}", flush=True)
        return False
    try:
        if soak:
            thermal_soak(prompts)
        for mode in modes:
            run_cell(bench, srv, variant, mmproj_variant, mode, prompts, 5, thermal)
    finally:
        srv.stop()
    return True


def main():
    prompts = B.parse_prompts()
    only = sys.argv[1:] if len(sys.argv) > 1 else None

    idle_w, _, _ = idle_baseline(60, "idle-start")
    if idle_w is None:
        print("FATAL: no power samples - is powermetrics running?"); sys.exit(1)
    bench = Bench(idle_w)

    for variant, model in VARIANTS:
        if only and variant not in only:
            continue
        do_variant(bench, variant, model, MMPROJ_AV, "audio+vision", MODES, prompts)

    if not only or "controls" in (only or []):
        # (a) text-512 with no projector at all
        do_variant(bench, "Q4_K_M", "models/Q4_K_M/Qolda-AVL-5B-Q4_K_M.gguf",
                   None, "none", ["text-512"], prompts)
        # (b) vision with the vision-only projector
        do_variant(bench, "Q4_K_M", "models/Q4_K_M/Qolda-AVL-5B-Q4_K_M.gguf",
                   MMPROJ_V, "vision-only", ["vision"], prompts)

    idle_end, _, _ = idle_baseline(60, "idle-end")
    print(f"\nidle start={idle_w} W  idle end={idle_end} W")
    with open("idle_baselines.json", "w") as f:
        json.dump({"idle_start_w": idle_w, "idle_end_w": idle_end}, f, indent=2)
    print("DONE ->", CSV_PATH)


if __name__ == "__main__":
    main()
