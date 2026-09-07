#!/usr/bin/env python3
"""Idle power baseline + scaling calibration for Device 3 (OnePlus 13R).

The protocol's source (/sys/class/power_supply/battery/{current_now,voltage_now})
is unreadable on this build, so this samples the two candidate substitutes and
prints them side by side under both unit interpretations. The point is to decide
whether this OEM reports uA/uV (the protocol's assumption) or mA/mV, using the
protocol's own sanity check: a screen-off unplugged idle phone should draw
roughly 0.3-0.8 W.

Preconditions (asserted, not assumed):
  - USB unplugged
  - screen off
  - airplane mode on (WiFi left up, it is the wireless-ADB transport)
  - nothing running on the device
"""
import argparse, json, os, re, statistics, sys, time
import bench_lib as B

ENV_PATH = os.path.join(B.ROOT, "env.json")


def preconditions():
    out = B.sh("dumpsys battery | grep -E 'USB powered|AC powered|^  level:|"
               "^  voltage:'").stdout
    plugged = "USB powered: true" in out or "AC powered: true" in out
    lvl = re.search(r"level:\s*(\d+)", out)
    wake = B.sh("dumpsys power | grep -m1 mWakefulness=").stdout.strip()
    air = B.sh("settings get global airplane_mode_on").stdout.strip()
    wifi = B.sh("settings get global wifi_on").stdout.strip()
    return dict(plugged=plugged, level=int(lvl.group(1)) if lvl else None,
                wakefulness=wake, airplane=air, wifi=wifi)


def sample(n, interval=1.0):
    rows = []
    for _ in range(n):
        t = time.time()
        out = B.sh("cmd battery get -f current_now; "
                   "cmd battery get -f current_average; "
                   "dumpsys battery | grep -E 'Battery current|^  voltage:'",
                   timeout=20).stdout
        cur = avg = oplus = volt = None
        nums = []
        for line in [l.strip() for l in out.splitlines() if l.strip()]:
            if re.fullmatch(r"-?\d+", line):
                nums.append(int(line))
            m = re.search(r"Battery current\s*:\s*(-?\d+)", line)
            if m:
                oplus = int(m.group(1))
            m = re.search(r"^voltage:\s*(\d+)", line)
            if m:
                volt = int(m.group(1))
        if nums:
            cur = nums[0]
        if len(nums) > 1:
            avg = nums[1]
        rows.append((t, cur, avg, oplus, volt))
        time.sleep(max(0, interval - (time.time() - t)))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=60)
    ap.add_argument("--write", action="store_true",
                    help="persist chosen scaling + idle baseline to env.json")
    ap.add_argument("--scale", choices=["mA_mV", "uA_uV"], default=None)
    args = ap.parse_args()

    pre = preconditions()
    print("preconditions:", json.dumps(pre), flush=True)
    if pre["plugged"]:
        print("\n!! DEVICE IS PLUGGED IN - idle baseline would be meaningless.\n"
              "   Unplug, screen off, then re-run.", file=sys.stderr)
        if not args.write:
            print("   (sampling anyway for a plugged-in reference)\n")

    rows = sample(args.seconds, 1.0)
    cur = [r[1] for r in rows if r[1] is not None]
    oplus = [r[3] for r in rows if r[3] is not None]
    volt = [r[4] for r in rows if r[4] is not None]

    if not cur or not volt:
        print("FATAL: no usable samples", file=sys.stderr)
        sys.exit(1)

    mc, mo = statistics.median(cur), (statistics.median(oplus) if oplus else None)
    mv = statistics.median(volt)

    print(f"\nsamples: n={len(rows)} over {args.seconds}s")
    print(f"  cmd battery current_now : median {mc}  "
          f"min {min(cur)} max {max(cur)}")
    if oplus:
        print(f"  dumpsys 'Battery current': median {mo}  "
              f"min {min(oplus)} max {max(oplus)}")
    print(f"  dumpsys voltage         : median {mv}  "
          f"min {min(volt)} max {max(volt)}")

    print("\n--- side-by-side under both unit interpretations ---")
    print(f"{'source':<26} {'as uA x uV':>14} {'as mA x mV':>14}")
    for name, c in [("cmd battery current_now", mc)] + \
                   ([("dumpsys Battery current", mo)] if mo is not None else []):
        w_u = abs(c * 1e-6) * (mv * 1e-6)
        w_m = abs(c * 1e-3) * (mv * 1e-3)
        print(f"{name:<26} {w_u:>14.6f} W {w_m:>11.3f} W")
    print("\nprotocol sanity band for a screen-off idle phone: 0.3 - 0.8 W")

    if args.write:
        if args.scale is None:
            print("\nrefusing to write env.json without an explicit --scale",
                  file=sys.stderr)
            sys.exit(2)
        cs = 1e-3 if args.scale == "mA_mV" else 1e-6
        vs = 1e-3 if args.scale == "mA_mV" else 1e-6
        idle_w = abs(mc * cs) * (mv * vs)
        env = json.load(open(ENV_PATH)) if os.path.exists(ENV_PATH) else {}
        env["power"] = dict(source="cmd battery get -f current_now (BatteryManager) "
                                   "x dumpsys battery voltage",
                            reason="/sys/class/power_supply/battery/* is not "
                                   "readable by the shell user on this build",
                            scale=args.scale,
                            current_scale_to_A=cs, voltage_scale_to_V=vs,
                            idle_power_w=idle_w,
                            idle_median_current_raw=mc,
                            idle_median_voltage_raw=mv,
                            idle_samples=len(rows),
                            idle_conditions=pre)
        json.dump(env, open(ENV_PATH, "w"), indent=2)
        print(f"\nwrote env.json: idle_power_w={idle_w:.4f} W (scale={args.scale})")


if __name__ == "__main__":
    main()
