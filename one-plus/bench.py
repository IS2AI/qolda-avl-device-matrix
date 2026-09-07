#!/usr/bin/env python3
"""Qolda-AVL-5B deployment benchmark - Device 3: OnePlus 13R (SM8650), CPU backend.

Runs on the Mac; drives llama-server on the phone over wireless ADB with USB
unplugged. Resumable: completed cells are read back from raw_runs.jsonl.

Thermal design (per the operator's revised plan, recorded in summary.md):
  sustained : full matrix, all variants x 6 modes x 5 reps, after 5 min of
              continuous generation. This is the primary result.
  cold      : Q4_K_M only, {text-512, vision, audio-30s} x 3 reps, with a
              genuine 10-minute idle before EVERY run. No cool-once-run-many.
  decay     : one 20-minute continuous text-512 run from cold, sampling decode
              throughput and zone temperature every 30 s -> thermal_decay.csv.
Zone temperatures are captured at the start and end of every run and carried in
the notes column, so thermal drift is in the data rather than implied.
"""
import argparse, csv, json, os, statistics, subprocess, sys, time
import bench_lib as B
import power_calc as PC

# Seconds of continued sampling after each request completes, so the register's
# behaviour after the final token is measured rather than assumed.
POST_REQUEST_LINGER_S = 16.0

# Per-request ceiling. The slowest legitimate cell measured is vision at ~215 s;
# 1800 s leaves a wide margin while surfacing a hung transport in minutes rather
# than the 49 minutes a 5400 s ceiling cost on the first cold vision run.
REQUEST_TIMEOUT_S = 1800

COMMIT   = "ea63b4d32ea1b66bdbe369be7f9443f6c00f8b31"
DEVCLASS = "flagship-smartphone"
DEVNAME  = "OnePlus 13R (CPH2691) / Snapdragon 8 Gen 3 SM8650 / 16 GB LPDDR5X"
BACKEND  = "CPU (ARM NEON/i8mm)"
PATCHED  = "yes"

MMPROJ_AV = "models/mmproj/mmproj-Qolda-AVL-5B-F16.gguf"
MMPROJ_V  = "models/mmproj/mmproj-Qolda-AVL-5B-vision-only-F16.gguf"

VARIANT_PATH = {
    "BF16":   "models/BF16/Qolda-AVL-5B-BF16.gguf",
    "Q8_0":   "models/Q8_0/Qolda-AVL-5B-Q8_0.gguf",
    "Q6_K":   "models/Q6_K/Qolda-AVL-5B-Q6_K.gguf",
    "Q5_K_M": "models/Q5_K_M/Qolda-AVL-5B-Q5_K_M.gguf",
    "Q4_K_M": "models/Q4_K_M/Qolda-AVL-5B-Q4_K_M.gguf",
}
# BF16 moved last by operator decision: it is the slowest and likeliest to
# thrash, so a complete dataset exists before it is attempted.
VARIANT_ORDER = ["Q4_K_M", "Q5_K_M", "Q6_K", "Q8_0", "BF16"]
MODES = ["text-128", "text-512", "text-2048", "vision", "audio-30s", "audio-10s"]

COLD_VARIANT = "Q4_K_M"
COLD_MODES = ["text-512", "vision", "audio-30s"]
COLD_REPS = 3

COLUMNS = ["device_class","device_name","backend","llamacpp_commit","patch_applied",
           "variant","mmproj_variant","mode","prompt_tokens","image_tokens",
           "audio_tokens","audio_seconds","gen_tokens","run_idx","thermal_state",
           "ttft_ms","encoder_ms","prefill_tps","decode_tps","total_ms",
           "peak_rss_gb","peak_vram_gb","avg_power_w","idle_power_w",
           "energy_j_per_1k_tok","notes",
           # Appended after the protocol's 26 columns so the leading schema stays
           # byte-compatible with Devices 1 and 2 (see deviation D10).
           "avg_power_w_raw","power_samples_used"]

CSV_PATH = os.path.join(B.ROOT, "results.csv")
RAW_PATH = os.path.join(B.ROOT, "raw_runs.jsonl")
ENV_PATH = os.path.join(B.ROOT, "env.json")
DECAY_PATH = os.path.join(B.ROOT, "thermal_decay.csv")

REPS = 5
COLD_IDLE_S = 600
SUSTAIN_S = 300
DECAY_S = 1200
DECAY_SAMPLE_S = 30
PEAK_VRAM = "unified (no discrete VRAM)"

# Zones reported in notes (full set goes to raw_runs.jsonl).
NOTE_ZONES = ["cpu-1-2-0", "cpuss-0", "shell_back", "skin-msm-therm"]

POWER = {}


def load_power_cfg():
    global POWER
    if os.path.exists(ENV_PATH):
        POWER = json.load(open(ENV_PATH)).get("power", {})
    return POWER


def watts(cur_raw, volt_mv):
    if cur_raw is None or volt_mv is None or not POWER:
        return None
    ca, vs = POWER.get("current_scale_to_A"), POWER.get("voltage_scale_to_V")
    if ca is None or vs is None:
        return None
    return abs(cur_raw * ca) * (volt_mv * vs)


def read_zones(zones):
    """Snapshot every resolved thermal zone in one adb call; milli-C."""
    if not zones:
        return {}
    cmd = "; ".join(f"echo \"{n} $(cat {p}/temp 2>/dev/null)\""
                    for n, p in zones.items())
    out = B.sh(cmd, timeout=30).stdout
    d = {}
    for line in out.splitlines():
        parts = line.strip().split()
        if len(parts) == 2 and parts[1].lstrip("-").isdigit():
            d[parts[0]] = int(parts[1])
    return d


def fmt_zones(tag, z):
    if not z:
        return ""
    bits = [f"{n}={z[n]/1000:.1f}C" for n in NOTE_ZONES if n in z]
    return f"{tag}[" + " ".join(bits) + "]" if bits else ""


# ---------------------------------------------------------------- resume
def done_keys():
    keys = set()
    if os.path.exists(RAW_PATH):
        for line in open(RAW_PATH):
            try:
                j = json.loads(line)
            except json.JSONDecodeError:
                continue
            # A transport failure is not a result -- it must be re-run on resume.
            # A load failure (server could not start, e.g. OOM) IS a result and
            # is kept so the matrix does not retry it forever.
            if not j.get("ok") and not j.get("load_failed"):
                continue
            keys.add((j["variant"], j["mmproj_variant"], j["mode"],
                      j["threads"], j["thermal_state"], j["run_idx"]))
    return keys


def append_raw(rec):
    with open(RAW_PATH, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- thermal states
# Seconds at the end of each cooldown spent polling /health over TCP. Android's
# WiFi firmware answers ICMP by offload while the host TCP stack sleeps, so a
# healthy ping does NOT mean a healthy socket: after a 10-minute idle the ~480 KB
# vision upload stalled for over half an hour (server did the work in 206 s;
# client saw first token at 1942 s). /health does no inference, so this warms the
# transport without adding measurable heat to a cold-labelled run. See D17.
KEEP_TCP_EVERY_S = 5


def cooldown(seconds, label="cold", zones=None):
    """Idle the device, keeping only the network stack alive.

    A /health round-trip every KEEP_TCP_EVERY_S stops the host from entering the
    deep sleep that stalls the next large upload (D17). It is a few microseconds
    of work per ping and does not measurably heat the SoC -- cooldowns still
    reach ~28 C SoC / ~24 C shell against a 23 C ambient -- so the run really is
    cold. The zone snapshot is taken at the end of the idle, before the final
    upload probe, so the recorded temperature is the cold one.
    """
    print(f"  [cooldown] idling {seconds}s before a {label} run "
          f"(TCP kept alive) ...", flush=True)
    t0 = time.time()
    while time.time() - t0 < seconds:
        try:
            B.health_ping()
        except Exception:
            pass
        time.sleep(KEEP_TCP_EVERY_S)
    z = read_zones(zones or {})
    probes, ok = B.wake_transport()
    print(f"  [cooldown] done {fmt_zones('tz', z)} "
          f"upload_probes={probes} ok={ok}", flush=True)
    if not ok:
        print("  [cooldown] WARNING: upload path still slow; run may stall",
              flush=True)
    return z


def sustain_load(prompts, seconds=SUSTAIN_S):
    print(f"  [sustain] continuous generation for {seconds}s ...", flush=True)
    t0 = time.time()
    n = 0
    ep, body = B.build_body("text-512", prompts)
    while time.time() - t0 < seconds:
        try:
            B.stream_request(ep, body, timeout=1800)
            n += 1
        except Exception as e:
            print(f"  [sustain] request failed: {e}", flush=True)
            break
    print(f"  [sustain] done after {n} requests, {time.time()-t0:.0f}s", flush=True)


# ---------------------------------------------------------------- one measured run
def measure(server, prompts, mode, variant, mmproj_variant, threads,
            thermal_state, run_idx, zones, idle_w, notes_extra=""):
    mem_before, swap_before = B.mem_and_swap()
    batt_before = B.battery_level()
    tz_start = read_zones(zones)

    # True per-run peak: reset the kernel high-water mark before the request.
    B.reset_vmhwm(server.pid)
    sampler = B.DeviceSampler(server.pid, interval=0.5, zones=zones)
    sampler.start()
    ep, body = B.build_body(mode, prompts)
    err, r = None, None
    # Transport failures (see D16) are retried once: the server does the work
    # correctly, only delivery fails, so a retry is cheap and does not change
    # what is being measured. Retries are recorded in notes.
    attempts = 0
    for attempt in (1, 2):
        attempts = attempt
        try:
            r = B.stream_request(ep, body, timeout=REQUEST_TIMEOUT_S)
            err = None
            # Transport-corruption guard. If the client's time-to-first-token far
            # exceeds the entire job the server reports doing, the bytes were
            # stalled in the network, not produced slowly by the device, and both
            # ttft_ms and decode_tps are meaningless for this row.
            tim = r.get("timings") or {}
            srv_total = (tim.get("prompt_ms") or 0) + (tim.get("predicted_ms") or 0)
            cli_ttft = (r["t_first"] - r["t_send"]) * 1000.0 if r["t_first"] else 0
            if srv_total and cli_ttft > 3.0 * srv_total:
                err = (f"transport stall: ttft {cli_ttft:.0f}ms vs server total "
                       f"{srv_total:.0f}ms (>3x)")
                r = None
                if attempt == 1:
                    print(f"     {err}; retrying once", flush=True)
                    time.sleep(5)
                    continue
            break
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            r = None
            if attempt == 1:
                print(f"     transport failure, retrying once: {err}", flush=True)
                time.sleep(5)
    # The moment the HTTP stream ends the WiFi link goes quiet and the host's
    # network stack sleeps, after which the next adb round-trip can stall for
    # minutes (observed: a 34 s request inside a 957 s measure() call, with the
    # sampler still ticking throughout). A cheap TCP round-trip immediately after
    # the request keeps the stack awake for the instrumentation that follows.
    # This is pure overhead reduction -- it happens after the measured window and
    # changes no reported number. See D18.
    try:
        B.health_ping()
    except Exception:
        pass
    # Zone temperatures must be read at the END OF GENERATION, before the linger
    # below, or they report a device that has already cooled and the per-run
    # thermal drift is destroyed.
    tz_end = read_zones(zones)
    # Keep sampling past the request so the register's lag-on-the-way-down can be
    # characterised from data rather than assumed (power_calc.analyse_tail).
    t_l = time.time()
    while time.time() - t_l < POST_REQUEST_LINGER_S:
        try:
            B.health_ping()          # keep the stack awake through the linger too
        except Exception:
            pass
        time.sleep(2.0)
    sampler.stop()
    tz_after_linger = read_zones(zones)
    batt_after = B.battery_level()
    mem_after, swap_after = B.mem_and_swap()

    rec = dict(variant=variant, mmproj_variant=mmproj_variant, mode=mode,
               threads=threads, thermal_state=thermal_state, run_idx=run_idx,
               mem_available_before_gb=mem_before, mem_available_after_gb=mem_after,
               swap_used_before_gb=swap_before, swap_used_after_gb=swap_after,
               battery_before=batt_before, battery_after=batt_after,
               tz_start=tz_start, tz_end=tz_end,
               tz_after_linger=tz_after_linger,
               error=err, attempts=attempts, notes_extra=notes_extra)

    if err or r is None or r["t_first"] is None:
        rec.update(ok=False, server_tail=server.tail(30), oom=server.oom_check())
        append_raw(rec)
        return rec

    t0, t1 = r["t_send"], r["t_end"]
    tim = r["timings"] or {}
    gen_n = tim.get("predicted_n") or r["stream_chunks"]
    ttft_ms = (r["t_first"] - r["t_send"]) * 1000.0
    dec_s = (r["t_last"] - r["t_first"]) or None
    decode_tps = ((gen_n - 1) / dec_s) if (dec_s and gen_n and gen_n > 1) else None
    prompt_n, prompt_ms = tim.get("prompt_n"), tim.get("prompt_ms")
    prefill_tps = (prompt_n / (prompt_ms / 1000.0)) if (prompt_n and prompt_ms) else None
    pred_ms = tim.get("predicted_ms")
    srv_tps = (gen_n / (pred_ms / 1000.0)) if (gen_n and pred_ms) else None
    ratio = (decode_tps / srv_tps) if (decode_tps and srv_tps) else None

    peak_rss_gb = sampler.peak_hwm_kb * 1024 / B.GIB if sampler.peak_hwm_kb else None

    # Power: raw (as-specified) and corrected (lead-in + sentinel trimmed).
    timed = sampler.power_timed()
    raw_w = PC.raw_mean_w(timed, t0, t1)
    avg_w, n_used = PC.corrected(timed, t0, t1)
    energy = None
    if avg_w is not None and idle_w is not None and dec_s and gen_n:
        energy = (avg_w - idle_w) * dec_s / gen_n * 1000.0

    rec.update(ok=True, ttft_ms=ttft_ms, decode_tps=decode_tps,
               prefill_tps=prefill_tps, total_ms=(t1 - t0) * 1000.0,
               gen_tokens=gen_n, prompt_n=prompt_n, prompt_ms=prompt_ms,
               predicted_n=tim.get("predicted_n"), predicted_ms=pred_ms,
               server_decode_tps=srv_tps, client_server_decode_ratio=ratio,
               peak_rss_gb=peak_rss_gb, peak_hwm_kb=sampler.peak_hwm_kb,
               avg_power_w=avg_w, avg_power_w_raw=raw_w,
               power_samples_used=n_used, power_sample_hz=B.POWER_HZ,
               power_lead_in_s=PC.LEAD_IN_S, power_tail_s=PC.TAIL_S,
               idle_power_w=idle_w,
               energy_j_per_1k_tok=energy,
               t_send=t0, t_first=r["t_first"], t_last=r["t_last"], t_end=t1,
               power_timed=timed,
               thermal_window=sampler.thermal_in(t0, t1),
               n_mem_samples=len(sampler.samples),
               text_head=r["text"][:200])
    append_raw(rec)
    return rec


# ---------------------------------------------------------------- thermal decay
def run_decay(prompts, zones, threads=6):
    """20 min of continuous text-512 generation from cold; sample every 30 s."""
    srv = B.Server(VARIANT_PATH[COLD_VARIANT], MMPROJ_AV, "server_decay.log",
                   threads=threads)
    srv.start()
    try:
        ep, body = B.build_body("text-512", prompts)
        for _ in range(3):
            B.stream_request(ep, body, timeout=3600)
        print(f"  [decay] warm-ups done; cooling {COLD_IDLE_S}s for a cold start",
              flush=True)
        cooldown(COLD_IDLE_S, "decay-cold", zones)

        rows = []
        t_start = time.time()
        last_sample = 0.0
        while time.time() - t_start < DECAY_S:
            r = B.stream_request(ep, body, timeout=3600)
            tim = r["timings"] or {}
            n = tim.get("predicted_n") or r["stream_chunks"]
            dec_s = (r["t_last"] - r["t_first"]) or None
            tps = ((n - 1) / dec_s) if (dec_s and n > 1) else None
            el = time.time() - t_start
            if el - last_sample >= DECAY_SAMPLE_S or not rows:
                z = read_zones(zones)
                lvl = B.battery_level()
                rows.append(dict(elapsed_s=round(el, 1), decode_tps=tps,
                                 ttft_ms=(r["t_first"] - r["t_send"]) * 1000.0,
                                 prompt_n=tim.get("prompt_n"),
                                 battery_level=lvl,
                                 **{f"tz_{k}_c": v / 1000.0 for k, v in z.items()}))
                last_sample = el
                print(f"  [decay] t={el:6.0f}s tps={tps:5.2f} "
                      f"{fmt_zones('tz', z)}", flush=True)
        keys = []
        for r in rows:
            for k in r:
                if k not in keys:
                    keys.append(k)
        with open(DECAY_PATH, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print(f"  [decay] wrote {DECAY_PATH} ({len(rows)} samples)", flush=True)
    finally:
        srv.stop()


# ---------------------------------------------------------------- CSV emit
def rec_to_row(rec, tokens_meta):
    mode = rec["mode"]
    tk = dict(tokens_meta.get(mode, {}))
    notes = []
    if rec.get("notes_extra"):
        notes.append(rec["notes_extra"])
    notes.append(f"threads={rec['threads']}")
    notes.append("mmap=off")
    notes.append("encoder_ms folded into ttft_ms (llama-server does not report it)")
    for tag, key in (("tz_start", "tz_start"), ("tz_end", "tz_end")):
        s = fmt_zones(tag, rec.get(key) or {})
        if s:
            notes.append(s)
    if rec.get("mem_available_before_gb") is not None:
        notes.append(f"MemAvailable_before={rec['mem_available_before_gb']:.2f}GB")
    sb, sa = rec.get("swap_used_before_gb"), rec.get("swap_used_after_gb")
    if sb is not None:
        notes.append(f"swap_used={sb:.2f}->{sa:.2f}GB")
        if sb > 0.5:
            notes.append(f"SWAP-AFFECTED: {sb:.2f} GB was in zram before this run; "
                         f"peak_rss_gb understates the true requirement because "
                         f"evicted pages are not resident")
    if rec.get("power_sample_hz"):
        notes.append(f"power_sampled_at={rec['power_sample_hz']:.2f}Hz "
                     f"lead_in={rec.get('power_lead_in_s')}s "
                     f"tail={rec.get('power_tail_s')}s")
    # Transport validation: decode_tps is measured client-side per the protocol,
    # so a degraded WiFi link would silently deflate it. Compare against the
    # server's own predicted_n/predicted_ms and flag any row where the transport
    # cost more than 5% (D11).
    sr = rec.get("server_decode_tps")
    ratio = rec.get("client_server_decode_ratio")
    if sr and ratio:
        notes.append(f"server_decode_tps={sr:.3g}; client/server={ratio:.3f}")
        if ratio < 0.95:
            notes.append(f"TRANSPORT-AFFECTED: client decode_tps is {100*(1-ratio):.0f}% "
                         f"below the server's own timing; network delivery, not the device")
    if (rec.get("attempts") or 1) > 1:
        notes.append(f"retried after transport failure (attempts={rec['attempts']})")
    n_used = rec.get("power_samples_used")
    if n_used is not None and rec.get("ok") and n_used < PC.MIN_USABLE_SAMPLES:
        notes.append(f"UNRELIABLE POWER: only {n_used} usable samples "
                     f"(<{PC.MIN_USABLE_SAMPLES}); avg_power_w and "
                     f"energy_j_per_1k_tok are weakly determined for this row")
    if not rec.get("ok"):
        notes.append("RUN FAILED")
        if rec.get("error"):
            notes.append(f"error={str(rec['error'])[:180]}")
    return {
        "device_class": DEVCLASS, "device_name": DEVNAME, "backend": BACKEND,
        "llamacpp_commit": COMMIT, "patch_applied": PATCHED,
        "variant": rec["variant"], "mmproj_variant": rec["mmproj_variant"],
        "mode": mode,
        "prompt_tokens": rec.get("prompt_n") or "",
        "image_tokens": tk.get("image_tokens", ""),
        "audio_tokens": tk.get("audio_tokens", ""),
        "audio_seconds": tk.get("audio_seconds", ""),
        "gen_tokens": rec.get("gen_tokens") or "",
        "run_idx": rec["run_idx"], "thermal_state": rec["thermal_state"],
        "ttft_ms": B.sig3(rec.get("ttft_ms")), "encoder_ms": "",
        "prefill_tps": B.sig3(rec.get("prefill_tps")),
        "decode_tps": B.sig3(rec.get("decode_tps")),
        "total_ms": B.sig3(rec.get("total_ms")),
        "peak_rss_gb": B.sig3(rec.get("peak_rss_gb")),
        "peak_vram_gb": PEAK_VRAM,
        "avg_power_w": B.sig3(rec.get("avg_power_w")),
        "idle_power_w": B.sig3(rec.get("idle_power_w")),
        "energy_j_per_1k_tok": B.sig3(rec.get("energy_j_per_1k_tok")),
        "notes": "; ".join(n for n in notes if n),
        "avg_power_w_raw": B.sig3(rec.get("avg_power_w_raw")),
        "power_samples_used": (rec.get("power_samples_used")
                               if rec.get("power_samples_used") is not None else ""),
    }


def write_csv(tokens_meta):
    rows = []
    for line in open(RAW_PATH):
        try:
            rows.append(rec_to_row(json.loads(line), tokens_meta))
        except json.JSONDecodeError:
            continue
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows)


# ---------------------------------------------------------------- plan
def build_plan(args):
    plan = []
    variants = [v for v in VARIANT_ORDER if v in args.variants.split(",")]
    states = args.thermal.split(",")

    if "sustained" in states:
        for v in variants:
            plan.append(dict(variant=v, model=VARIANT_PATH[v], mmproj=MMPROJ_AV,
                             mmproj_variant="audio+vision",
                             modes=args.modes.split(","), threads=args.threads,
                             thermal="sustained", reps=args.reps,
                             per_run_cooldown=False))
        if args.controls:
            plan.append(dict(variant="Q4_K_M", model=VARIANT_PATH["Q4_K_M"],
                             mmproj=None, mmproj_variant="none",
                             modes=["text-512"], threads=args.threads,
                             thermal="sustained", reps=args.reps,
                             per_run_cooldown=False))
            plan.append(dict(variant="Q4_K_M", model=VARIANT_PATH["Q4_K_M"],
                             mmproj=MMPROJ_V, mmproj_variant="vision-only",
                             modes=["vision"], threads=args.threads,
                             thermal="sustained", reps=args.reps,
                             per_run_cooldown=False))
            for t in (4, 8):
                plan.append(dict(variant="Q4_K_M", model=VARIANT_PATH["Q4_K_M"],
                                 mmproj=MMPROJ_AV, mmproj_variant="audio+vision",
                                 modes=["text-512"], threads=t,
                                 thermal="sustained", reps=args.reps,
                                 per_run_cooldown=False))

    if "cold" in states:
        plan.append(dict(variant=COLD_VARIANT, model=VARIANT_PATH[COLD_VARIANT],
                         mmproj=MMPROJ_AV, mmproj_variant="audio+vision",
                         modes=COLD_MODES, threads=args.threads,
                         thermal="cold", reps=COLD_REPS,
                         per_run_cooldown=True))
    return plan


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default=",".join(VARIANT_ORDER))
    ap.add_argument("--modes", default=",".join(MODES))
    ap.add_argument("--thermal", default="sustained,cold")
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--threads", type=int, default=6)
    ap.add_argument("--decay", action="store_true", help="run the 20-min decay curve")
    ap.add_argument("--csv-only", action="store_true")
    args = ap.parse_args()

    load_power_cfg()
    tokens_meta = {}
    tm_path = os.path.join(B.ROOT, "token_census.json")
    if os.path.exists(tm_path):
        tokens_meta = json.load(open(tm_path)).get("modes", {})

    if args.csv_only:
        print(f"wrote {CSV_PATH} ({write_csv(tokens_meta)} rows)")
        return

    prompts = B.parse_prompts()
    zones = B.resolve_thermal_zones()
    idle_w = POWER.get("idle_power_w")
    print(f"zones={len(zones)} idle_power_w={idle_w} "
          f"transport={B.ADB_SERIAL}", flush=True)

    if args.decay:
        run_decay(prompts, zones, args.threads)
        return

    done = done_keys()
    print(f"{len(done)} cells already recorded", flush=True)

    for blk in build_plan(args):
        need = [(m, i) for m in blk["modes"] for i in range(1, blk["reps"] + 1)
                if (blk["variant"], blk["mmproj_variant"], m, blk["threads"],
                    blk["thermal"], i) not in done]
        tag = (f"{blk['variant']}_{blk['mmproj_variant']}_t{blk['threads']}"
               f"_{blk['thermal']}")
        if not need:
            print(f"SKIP {tag} (complete)", flush=True)
            continue
        print(f"\n=== {tag} : {len(need)} runs ===", flush=True)

        srv = B.Server(blk["model"], blk["mmproj"], f"server_{tag}.log",
                       threads=blk["threads"])
        mem_pre = B.mem_available_gb()
        try:
            load_s = srv.start()
            print(f"  server up in {load_s:.1f}s pid={srv.pid} "
                  f"MemAvailable_pre={mem_pre:.2f}GB", flush=True)
        except Exception as e:
            oom = srv.oom_check()
            print(f"  !! SERVER FAILED TO LOAD: {e}", flush=True)
            for m, i in need:
                append_raw(dict(variant=blk["variant"],
                                mmproj_variant=blk["mmproj_variant"], mode=m,
                                threads=blk["threads"],
                                thermal_state=blk["thermal"], run_idx=i, ok=False,
                                error=str(e)[:3000], oom=oom, load_failed=True,
                                mem_available_before_gb=mem_pre))
            srv.stop()
            continue

        # 3 discarded warm-ups per server start.
        wu = blk["modes"][0]
        ep, body = B.build_body(wu, prompts)
        for k in range(3):
            try:
                B.stream_request(ep, body, timeout=5400)
            except Exception as e:
                print(f"  warmup {wu} #{k+1} failed: {e}", flush=True)
                break

        if blk["thermal"] == "sustained":
            sustain_load(prompts, SUSTAIN_S)

        for m, i in need:
            lvl = B.battery_level()
            if lvl is not None and lvl < 20:
                print(f"  !! battery {lvl}% below 20% floor - stopping", flush=True)
                srv.stop()
                write_csv(tokens_meta)
                return
            if blk["per_run_cooldown"]:
                cooldown(COLD_IDLE_S, blk["thermal"], zones)
            t0 = time.time()
            rec = measure(srv, prompts, m, blk["variant"], blk["mmproj_variant"],
                          blk["threads"], blk["thermal"], i, zones, idle_w)
            print(f"  {m} run{i} {'OK' if rec.get('ok') else 'FAIL'} "
                  f"ttft={rec.get('ttft_ms') or 0:.0f}ms "
                  f"dec={rec.get('decode_tps') or 0:.2f}tps "
                  f"rss={rec.get('peak_rss_gb') or 0:.2f}GB "
                  f"batt={lvl}% ({time.time()-t0:.0f}s)", flush=True)
            if not rec.get("ok"):
                print(f"     err={rec.get('error')}", flush=True)
            write_csv(tokens_meta)

        srv.stop()

    print(f"\nwrote {CSV_PATH} ({write_csv(tokens_meta)} rows)")


if __name__ == "__main__":
    main()
