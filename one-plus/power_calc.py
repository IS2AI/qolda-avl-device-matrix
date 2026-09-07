"""Corrected power derivation for Device 3 (OnePlus 13R).

Kept separate from bench.py so the power columns can be recomputed from
raw_runs.jsonl under any trimming rule without re-running the matrix.

Why a correction is needed
--------------------------
The protocol's power source (/sys/class/power_supply/battery/*) is unreadable on
this build, so current comes from the BatteryManager register via
`cmd battery get -f current_now`. That register has two measured defects:

1. It refreshes on its own schedule, not on read. Measured across 71 repeat-runs
   of consecutive identical samples at 1 Hz: median 2.0 s, mean 2.46 s, max 7 s
   between value changes. Sampling faster than that returns duplicates, which
   inflate the apparent sample count without adding information. Power is
   therefore sampled at 0.25 Hz (POWER_INTERVAL_S = 4 s in bench_lib).

2. It lags the load. At the start of a run it still reports the idle gap between
   runs. The settling index (first sample differing from the run's opening value)
   was measured at [1, 1, 1, 2, 2, 2, 5, 7] seconds across 8 runs -> max 7 s.

It also emits exact 0 mA sentinels while the device is drawing several watts,
which is physically impossible and is a failed read rather than a measurement.

Effect of leaving this uncorrected: mean power over the full window had a 69%
run-to-run spread on identical work, and because a fixed lead-in is a much larger
fraction of a 27 s text run than of a 190 s vision run, the bias is
mode-dependent -- text modes would read systematically low against audio/vision,
corrupting exactly the cross-mode energy comparison the paper needs.
"""
import statistics as st

# Smallest multiple of the 4 s power-sampling period that covers the measured
# maximum settling time of 7 s. Recorded in summary.md with its justification.
LEAD_IN_S = 8.0

# Tail trim. The register lags on the way down as well, so samples near the end
# of the window still report load -- which is correct for a steady-state run and
# argues against trimming. Set from measured post-request decay by
# analyse_tail(); 0.0 means the measurement showed no tail contamination.
TAIL_S = 0.0

# Rows with fewer than this many surviving samples have an unreliable mean and
# are flagged in notes.
MIN_USABLE_SAMPLES = 8


def _mv(samples):
    volts = [v for _, _, _, v in samples if v]
    return (st.mean(volts) / 1000.0) if volts else None


def raw_mean_w(samples, t_send, t_end):
    """As-specified: mean over the whole request window, every sample kept."""
    w = [s for s in samples if t_send - 1.0 <= s[0] <= t_end + 1.0]
    mv = _mv(w)
    if not w or mv is None:
        return None
    return st.mean([abs(c) / 1000.0 * mv for _, c, _, _ in w])


def corrected(samples, t_send, t_end,
              lead_in=LEAD_IN_S, tail=TAIL_S):
    """Mean over the window after dropping the lead-in, the tail, and 0 sentinels.

    Returns (watts, n_used).
    """
    lo, hi = t_send + lead_in, t_end - tail
    w = [s for s in samples if lo <= s[0] <= hi and s[1]]
    mv = _mv(w) or _mv(samples)
    if not w or mv is None:
        return None, 0
    return st.mean([abs(c) / 1000.0 * mv for _, c, _, _ in w]), len(w)


def analyse_tail(recs, window_s=20.0):
    """Characterise register behaviour after the final token.

    For each run, compare samples inside the request window against those taken
    after it. If post-request values remain at load level, the register is still
    draining its lag and the in-window tail is reporting genuine load (no trim
    warranted). If they drop immediately, the tail is uncontaminated either way.
    """
    out = []
    for r in recs:
        ps = r.get("power_timed") or []
        te = r.get("t_end")
        if not ps or te is None:
            continue
        inw = [c for t, c, _, _ in ps if t <= te and c]
        post = [(round(t - te, 1), c) for t, c, _, _ in ps if t > te]
        if inw and post:
            out.append(dict(mode=r["mode"], run=r["run_idx"],
                            in_window_median=st.median(inw),
                            post=post[:6]))
    return out
