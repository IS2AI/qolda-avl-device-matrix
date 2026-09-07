"""Shared helpers for the Qolda-AVL-5B deployment benchmark.

Device 3: OnePlus 13R (CPH2691), Snapdragon 8 Gen 3 / SM8650, CPU backend.

Topology: llama-server runs detached on the phone under nohup; this harness runs
on the Mac and reaches it over wireless ADB (USB unplugged during measured runs).
No interactive shell is held open on the device and nothing is installed there.

Measurement definitions are carried over verbatim from Device 2 (bench_lib.py in
../qolda-avl-gguf) so the three devices stay comparable:
  ttft_ms     = t_first_chunk - t_send
  decode_tps  = (generated_tokens - 1) / (t_last_chunk - t_first_chunk)
  prefill_tps = prompt_n / prompt_ms  (from the server `timings` object)
"""
import base64, http.client, json, os, re, socket, subprocess, threading, time
import urllib.request, urllib.error

# ---------------------------------------------------------------- device paths
DEV_ROOT = "/data/local/tmp/qolda"
DEV_BIN  = f"{DEV_ROOT}/bin"
DEV_ART  = f"{DEV_ROOT}/art"
DEV_LOGS = f"{DEV_ROOT}/logs"

# The measured request path is a DIRECT TCP connection to the phone over WiFi,
# not `adb forward`. adb forward tunnels TCP through adb's own multiplexing
# protocol, which was measured to cost 2-17% of decode throughput in the healthy
# case and up to 95% when the link degraded (client 0.36 tps against a
# server-reported 7.38 tps). Direct HTTP measures client/server decode agreement
# at 0.990-0.998. llama-server therefore binds 0.0.0.0 and the harness connects
# to DEVICE_IP. See deviation D11.
DEVICE_IP = os.environ.get("DEVICE_IP", "192.168.0.138")
BIND_HOST, PORT = "0.0.0.0", 8077
BASE = f"http://{DEVICE_IP}:{PORT}"

ROOT = os.path.abspath(os.path.dirname(__file__))
GIB = 1024 ** 3

# Thermal zones of interest, resolved once at startup (see summary.md mapping).
THERMAL_ZONES = {
    "cpu-0-0-0": None, "cpu-1-2-0": None, "cpu-2-0-0": None,
    "cpuss-0": None, "gpuss-0": None, "ddr": None,
    "shell_back": None, "shell_front": None, "skin-msm-therm": None,
}


# ---------------------------------------------------------------- adb plumbing
# Measured runs happen over wireless ADB with USB unplugged. Pin the transport
# explicitly so the harness never binds to a USB transport that happens to be
# present during setup.
ADB_SERIAL = os.environ.get("ADB_SERIAL", "192.168.0.138:5555")


def adb(*args, timeout=120, check=False):
    """Run an adb command against the pinned transport, return CompletedProcess."""
    pre = ["adb"] + (["-s", ADB_SERIAL] if ADB_SERIAL else [])
    p = subprocess.run([*pre, *args], capture_output=True, text=True, timeout=timeout)
    if check and p.returncode != 0:
        raise RuntimeError(f"adb {' '.join(args)} failed rc={p.returncode}: {p.stderr}")
    return p


def sh(cmd, timeout=120, check=False):
    """Run a single shell command on the device (discrete invocation, no held shell)."""
    return adb("shell", cmd, timeout=timeout, check=check)


def adb_transport():
    """Return the current adb transport string (usb serial or ip:port)."""
    out = adb("devices", "-l").stdout.splitlines()
    for line in out[1:]:
        if "\tdevice" in line or " device " in line:
            return line.split()[0]
    return None


def forward(port=PORT):
    adb("forward", "--remove", f"tcp:{port}", timeout=20)
    adb("forward", f"tcp:{port}", f"tcp:{port}", timeout=20, check=True)


def resolve_thermal_zones():
    """Map zone type -> /sys path once; cached in THERMAL_ZONES."""
    out = sh("for z in /sys/class/thermal/thermal_zone*; do "
             "echo \"$(cat $z/type 2>/dev/null) $z\"; done").stdout
    for line in out.splitlines():
        parts = line.strip().split()
        if len(parts) == 2 and parts[0] in THERMAL_ZONES:
            THERMAL_ZONES[parts[0]] = parts[1]
    return {k: v for k, v in THERMAL_ZONES.items() if v}


def mem_and_swap():
    """MemAvailable and swap-in-use, both GiB, in one adb call.

    Swap matters on this device: with --no-mmap the weights are anonymous memory,
    and once the working set exceeds RAM the kernel evicts them to zram. That
    makes peak_rss_gb UNDERSTATE the requirement -- a swapping process shows a
    smaller resident set, not a larger one (observed on Q8_0: peak RSS fell from
    6.80 GB to 4.92 GB as ~4.7 GB was pushed to zram). Both numbers are needed to
    tell "fits comfortably" from "technically runs while thrashing".
    """
    out = sh("grep -E 'MemAvailable|SwapTotal|SwapFree' /proc/meminfo").stdout
    d = {}
    for line in out.splitlines():
        m = re.match(r"(\w+):\s+(\d+)", line.strip())
        if m:
            d[m.group(1)] = int(m.group(2))
    avail = d.get("MemAvailable", 0) * 1024 / GIB
    swap_used = (d.get("SwapTotal", 0) - d.get("SwapFree", 0)) * 1024 / GIB
    return avail, swap_used


def mem_available_gb():
    """MemAvailable from /proc/meminfo, in GiB."""
    out = sh("grep MemAvailable /proc/meminfo").stdout
    m = re.search(r"(\d+)", out)
    return int(m.group(1)) * 1024 / GIB if m else None


def meminfo_snapshot():
    out = sh("grep -E 'MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree|"
             "Cached|Buffers' /proc/meminfo").stdout
    d = {}
    for line in out.splitlines():
        m = re.match(r"(\w+):\s+(\d+)", line.strip())
        if m:
            d[m.group(1)] = int(m.group(2))
    return d


def reset_vmhwm(pid):
    """Reset the kernel's VmHWM high-water mark for `pid`.

    VmHWM is peak RSS since PROCESS start, and one llama-server serves every run
    in a block, so without this each run would inherit the maximum of all earlier
    runs (audio-10s would report audio-30s's larger peak). Writing 5 to clear_refs
    resets the mark, making VmHWM a true per-run peak. Verified on this device.
    """
    return sh(f"echo 5 > /proc/{pid}/clear_refs", timeout=20).returncode == 0


def battery_level():
    out = sh("dumpsys battery | grep -E '^  level:'").stdout
    m = re.search(r"(\d+)", out)
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------- prompts
def parse_prompts(path=None):
    """Split on opening markers only; bodies run to the next marker or EOF."""
    path = path or os.path.join(ROOT, "prompts_text.txt")
    lines = open(path, encoding="utf-8").read().split("\n")
    marks = [(i, l.strip()) for i, l in enumerate(lines) if l.startswith("<<<PROMPT_")]
    out = {}
    for k, (i, name) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(lines)
        out[name] = "\n".join(lines[i + 1:end]).rstrip()
    ne = [v for v in out.values() if v.strip()]
    if len(ne) != 3:
        raise SystemExit(f"FATAL: expected 3 non-empty prompts, got {len(ne)}")
    return out


def b64file(p):
    return base64.b64encode(open(p, "rb").read()).decode()


# ---------------------------------------------------------------- sampler
# The BatteryManager current register refreshes on its own schedule, measured on
# this device at median 2.0 s / mean 2.46 s / max 7 s between value changes.
# Sampling faster than that returns the same value repeatedly, which inflates the
# apparent sample count without adding information. Power is therefore sampled at
# 0.25 Hz (every 4 s), above the mean refresh interval, so samples are close to
# independent. Memory cadence is set separately below.
POWER_INTERVAL_S = 4.0
POWER_HZ = 1.0 / POWER_INTERVAL_S

# Memory sampling cadence: the protocol's 500 ms, retained.
# An earlier attempt to slow this to 2 s (on the theory that adb round-trips were
# competing with the measured HTTP stream) made delivery dramatically WORSE --
# client/server decode ratio fell to 0.444 and 0.130. The causation runs the other
# way: the WiFi link enters power-save between packets, and frequent adb traffic
# keeps the radio awake. Sampling at 500 ms is both protocol-compliant and helpful.
# The link is held awake properly by a host-side ICMP keepalive (D13), and long
# silent prefills are protected by TCP keepalive on the client socket (D16).


class DeviceSampler(threading.Thread):
    """One combined adb call per tick: RSS/HWM, plus power + thermal on slow ticks.

    Memory is sampled every `interval` s (500 ms, per protocol). Power and
    thermal are recorded every POWER_INTERVAL_S (0.25 Hz) because the underlying
    register cannot supply independent samples faster than that. Both candidate
    power sources and a timestamp are captured on every power tick, so the power
    column can be recomputed afterwards under any trimming rule without re-running.

    Sampling deliberately continues past the end of the request (see `linger`) so
    the register's lag-on-the-way-down can be characterised from real data.
    """

    def __init__(self, pid, interval=0.5, zones=None,
                 power_interval=POWER_INTERVAL_S):
        super().__init__(daemon=True)
        self.pid, self.interval = pid, interval
        self.power_interval = power_interval
        self.zones = zones or {}
        self.samples = []          # (t, rss_kb, hwm_kb)
        self.power = []            # (t, current_now_raw, oplus_current_raw, voltage_mv)
        self.thermal = []          # (t, {zone: milli_c})
        self.peak_hwm_kb = 0
        self.peak_rss_kb = 0
        self._last_power_t = 0.0
        self._stop = threading.Event()

    def _tick_cmd(self, with_power):
        parts = [f"cat /proc/{self.pid}/status 2>/dev/null | grep -E 'VmRSS|VmHWM'"]
        if with_power:
            parts.append("echo ---PWR---")
            parts.append("cmd battery get -f current_now 2>/dev/null")
            parts.append("dumpsys battery 2>/dev/null | grep -E "
                         "'Battery current|^  voltage:'")
            parts.append("echo ---THM---")
            for name, path in self.zones.items():
                parts.append(f"echo \"{name} $(cat {path}/temp 2>/dev/null)\"")
        return "; ".join(parts)

    def run(self):
        while not self._stop.is_set():
            t = time.time()
            with_power = (t - self._last_power_t) >= self.power_interval
            if with_power:
                self._last_power_t = t
            try:
                out = sh(self._tick_cmd(with_power), timeout=15).stdout
            except Exception:
                self._stop.wait(self.interval)
                continue
            self._parse(t, out, with_power)
            self._stop.wait(self.interval)

    def _parse(self, t, out, with_power):
        mem_part = out.split("---PWR---")[0]
        rss = hwm = None
        for line in mem_part.splitlines():
            m = re.match(r"VmRSS:\s+(\d+)", line.strip())
            if m:
                rss = int(m.group(1))
            m = re.match(r"VmHWM:\s+(\d+)", line.strip())
            if m:
                hwm = int(m.group(1))
        if rss is not None:
            self.samples.append((t, rss, hwm))
            self.peak_rss_kb = max(self.peak_rss_kb, rss)
        if hwm is not None:
            self.peak_hwm_kb = max(self.peak_hwm_kb, hwm)

        if not with_power or "---PWR---" not in out:
            return
        pwr_part = out.split("---PWR---")[1].split("---THM---")[0]
        thm_part = out.split("---THM---")[1] if "---THM---" in out else ""

        cur = oplus = volt = None
        lines = [l.strip() for l in pwr_part.splitlines() if l.strip()]
        for l in lines:
            if re.fullmatch(r"-?\d+", l):
                cur = int(l)
            m = re.search(r"Battery current\s*:\s*(-?\d+)", l)
            if m:
                oplus = int(m.group(1))
            m = re.search(r"^voltage:\s*(\d+)", l)
            if m:
                volt = int(m.group(1))
        self.power.append((t, cur, oplus, volt))

        zt = {}
        for l in thm_part.splitlines():
            parts = l.strip().split()
            if len(parts) == 2 and re.fullmatch(r"-?\d+", parts[1]):
                zt[parts[0]] = int(parts[1])
        if zt:
            self.thermal.append((t, zt))

    def stop(self):
        self._stop.set()
        self.join(timeout=10)
        return self.peak_hwm_kb, self.peak_rss_kb

    # ---- windowed reductions -------------------------------------------------
    def peak_rss_gb_in(self, t0, t1):
        w = [r for t, r, h in self.samples if t0 - 0.6 <= t <= t1 + 0.6]
        return (max(w) * 1024 / GIB) if w else None

    def power_in(self, t0, t1):
        """Return list of (current_raw, oplus_raw, voltage_mv) inside the window.

        Retained for the as-specified `avg_power_w_raw` figure: mean over the
        whole request window, every sample, exactly as the protocol states.
        """
        return [(c, o, v) for t, c, o, v in self.power
                if t0 - 1.0 <= t <= t1 + 1.0 and c is not None]

    def power_timed(self):
        """All power samples with timestamps, including any past the request end.

        The corrected figure is derived from these in power_calc.py, so any
        trimming rule can be re-applied later without re-running the matrix.
        """
        return [(t, c, o, v) for t, c, o, v in self.power if c is not None]

    def thermal_in(self, t0, t1):
        w = [zt for t, zt in self.thermal if t0 - 1.0 <= t <= t1 + 1.0]
        if not w:
            return {}
        keys = set().union(*[set(z) for z in w])
        return {k: (min(z[k] for z in w if k in z),
                    max(z[k] for z in w if k in z)) for k in keys}


# ---------------------------------------------------------------- server
class Server:
    """llama-server launched detached on-device via nohup; no shell held open."""

    def __init__(self, model, mmproj, log_name, threads=6, ctx=4096, extra=None):
        self.model, self.mmproj = model, mmproj
        self.log = f"{DEV_LOGS}/{log_name}"
        self.threads, self.ctx = threads, ctx
        self.extra = extra or []
        self.pid = None

    def cmd(self):
        c = [f"{DEV_BIN}/llama-server",
             "-m", f"{DEV_ROOT}/{self.model}",
             "--host", BIND_HOST, "--port", str(PORT),
             "-c", str(self.ctx), "-b", "2048", "-ub", "512",
             "--no-mmap", "--parallel", "1", "--no-webui",
             "--reasoning-format", "none",
             "-t", str(self.threads)]
        if self.mmproj:
            c += ["--mmproj", f"{DEV_ROOT}/{self.mmproj}"]
        return c + self.extra

    def cmdline(self):
        return " ".join(self.cmd())

    def start(self, timeout=900):
        self.kill_stale()
        # stdin must be detached as well, or `adb shell` blocks holding the
        # connection open instead of returning the pid. `cd` is separated with
        # `;` so that `&` backgrounds only the nohup, not an AND-list subshell
        # (otherwise $! is the subshell and /proc/<pid> is the wrong process).
        launch = (f"cd {DEV_ROOT}; export LD_LIBRARY_PATH={DEV_BIN}; "
                  f"nohup {self.cmdline()} > {self.log} 2>&1 < /dev/null "
                  f"& echo $!")
        out = sh(launch, timeout=60).stdout.strip()
        m = re.search(r"(\d+)", out)
        if not m:
            raise RuntimeError(f"could not read server pid, got: {out!r}")
        self.pid = int(m.group(1))

        # Confirm against the real ELF process; the launch shell may still have
        # interposed a subshell. pgrep -x matches on comm, not the command line.
        for _ in range(20):
            real = sh("pgrep -x llama-server", timeout=20).stdout.split()
            real = [int(x) for x in real if x.strip().isdigit()]
            if real:
                if len(real) > 1:
                    raise RuntimeError(f"multiple llama-server processes {real}; "
                                       "refusing to guess which one is being measured")
                self.pid = real[0]
                break
            time.sleep(0.5)
        # No adb forward: the measured path is a direct TCP connection (D11).

        t0 = time.time()
        while time.time() - t0 < timeout:
            if not self.alive():
                raise RuntimeError(f"server died during load\n{self.tail(60)}")
            try:
                with urllib.request.urlopen(f"{BASE}/health", timeout=3) as r:
                    if r.status == 200:
                        return time.time() - t0
            except Exception:
                time.sleep(0.7)
        raise RuntimeError(f"server not ready in {timeout}s\n{self.tail(60)}")

    def alive(self):
        return sh(f"[ -d /proc/{self.pid} ] && echo YES || echo NO",
                  timeout=20).stdout.strip().endswith("YES")

    def oom_check(self):
        """Look for a kernel OOM kill of our pid in the last kernel log."""
        out = sh(f"dmesg 2>/dev/null | tail -400 | grep -iE "
                 f"'out of memory|oom-kill|Killed process' | tail -8").stdout
        return out.strip()

    def tail(self, n=40):
        return sh(f"tail -n {n} {self.log}", timeout=30).stdout

    def kill_stale(self):
        """Kill any running llama-server and WAIT for the port to be released.

        `pkill -f llama-server` cannot be used: -f matches the full command line,
        which includes the adb shell process running the pkill itself, so the
        shell kills itself before reaching the server and the stale process
        survives. `pkill -x` matches on comm and is safe.

        Waiting matters as much as killing: a new server that starts before the
        old one releases port 8077 dies with "couldn't bind HTTP server socket",
        after which start() would find the OLD pid via pgrep and silently drive
        the stale process instead.
        """
        sh("pkill -x llama-server 2>/dev/null; true", timeout=30)
        for _ in range(60):
            time.sleep(0.5)
            out = sh("pgrep -x llama-server", timeout=20).stdout.split()
            if not [x for x in out if x.strip().isdigit()]:
                break
        else:
            sh("pkill -9 -x llama-server 2>/dev/null; true", timeout=30)
            time.sleep(2.0)
        time.sleep(1.5)

    def stop(self):
        if self.pid:
            sh(f"kill {self.pid} 2>/dev/null; true", timeout=30)
            t0 = time.time()
            while time.time() - t0 < 30 and self.alive():
                time.sleep(0.5)
            if self.alive():
                sh(f"kill -9 {self.pid} 2>/dev/null; true", timeout=30)
        self.kill_stale()
        time.sleep(1.5)


# ---------------------------------------------------------------- requests
GEN = dict(n_predict=256, temperature=0.7, top_p=0.95, top_k=20,
           seed=1234, ignore_eos=True, cache_prompt=False, stream=True)

VISION_INSTR = ("Суреттегі нысандарды, олардың өзара орналасуын, "
                "түстері мен көрінетін жазуларды егжей-тегжейлі сипаттап бер.")
AUDIO_INSTR = "Аудиодағы сөйлеуді сөзбе-сөз жазып шық."

PROMPT_KEY = {"text-128": "<<<PROMPT_128>>>",
              "text-512": "<<<PROMPT_512>>>",
              "text-2048": "<<<PROMPT_2048>>>"}


def build_body(mode, prompts):
    """Returns (endpoint, body)."""
    if mode.startswith("text"):
        b = dict(GEN)
        b["prompt"] = prompts[PROMPT_KEY[mode]]
        return "/completion", b
    if mode == "vision":
        content = [
            {"type": "image_url",
             "image_url": {"url": "data:image/jpeg;base64,"
                                  + b64file(os.path.join(ROOT, "bench_image.jpg"))}},
            {"type": "text", "text": VISION_INSTR},
        ]
    elif mode.startswith("audio"):
        wav = "bench_audio_30s.wav" if mode == "audio-30s" else "bench_audio_10s.wav"
        content = [
            {"type": "input_audio",
             "input_audio": {"data": b64file(os.path.join(ROOT, wav)),
                             "format": "wav"}},
            {"type": "text", "text": AUDIO_INSTR},
        ]
    else:
        raise ValueError(mode)
    b = dict(GEN)
    b.pop("n_predict")
    b.update(max_tokens=256, messages=[{"role": "user", "content": content}])
    return "/v1/chat/completions", b


class _KeepAliveHTTPConnection(http.client.HTTPConnection):
    """HTTPConnection with aggressive TCP keepalive.

    Encoder-bound requests go silent on the socket for a long time -- vision
    spends ~172 s in prefill before the first byte of response. After a cold-run
    cooldown the WiFi path is idle enough that something between the two hosts
    drops that connection, and the client then blocks until it sees a reset
    (observed: server completed in 211 s, client hung 2963 s then
    ConnectionResetError). TCP keepalive probes keep the connection referenced
    during the silent prefill.
    """

    def connect(self):
        super().connect()
        s = self.sock
        s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        # macOS spells the idle-before-first-probe option TCP_KEEPALIVE.
        for opt, val in (("TCP_KEEPALIVE", 15), ("TCP_KEEPIDLE", 15),
                         ("TCP_KEEPINTVL", 5), ("TCP_KEEPCNT", 8)):
            if hasattr(socket, opt):
                try:
                    s.setsockopt(socket.IPPROTO_TCP, getattr(socket, opt), val)
                except OSError:
                    pass


class _KeepAliveHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(_KeepAliveHTTPConnection, req)


_OPENER = urllib.request.build_opener(_KeepAliveHandler)


def health_ping(timeout=5):
    """Cheap TCP round-trip to keep the host's network stack awake (D17)."""
    with _OPENER.open(BASE + "/health", timeout=timeout) as r:
        return r.read()


# Upload-path probe. It is specifically the large POST upload to a freshly-idle
# host that stalls (vision ~480 KB of base64, audio-30s ~1.3 MB), not the
# download. A bogus path cannot be used -- llama-server answers 404 and closes
# before reading the body, which just yields a broken pipe. /tokenize consumes
# the whole body and runs no inference, so it exercises the failing path at
# negligible CPU cost, which matters because this runs during a cold cooldown.
_PROBE_BODY = json.dumps({"content": "x " * 60000}).encode()   # ~120 KB


def upload_probe(timeout=60):
    """POST a large body to /tokenize and return seconds elapsed."""
    req = urllib.request.Request(BASE + "/tokenize", data=_PROBE_BODY,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with _OPENER.open(req, timeout=timeout) as r:
        r.read()
    return time.time() - t0


def wake_transport(max_wait=120, target_s=4.0):
    """Probe the upload path until it is demonstrably fast.

    Returns (probes, ok). A healthy probe of this size completes well under a
    second; a host whose network stack is still asleep takes many seconds.
    """
    t0 = time.time()
    probes = []
    while time.time() - t0 < max_wait:
        try:
            el = upload_probe()
            probes.append(round(el, 2))
            if el <= target_s:
                return probes, True
        except Exception:
            probes.append(None)
        time.sleep(1.0)
    return probes, False


def stream_request(endpoint, body, timeout=3600):
    """Issue a streaming request; return timing dict."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + endpoint, data=data,
                                 headers={"Content-Type": "application/json"})
    t_send = time.time()
    t_first = t_last = None
    ntok = 0
    timings = None
    text = []
    with _OPENER.open(req, timeout=timeout) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                continue
            try:
                j = json.loads(payload)
            except json.JSONDecodeError:
                continue
            piece = ""
            if "choices" in j and j["choices"]:
                d = j["choices"][0].get("delta") or {}
                # Thinking checkpoints may route text to reasoning_content;
                # both are generated tokens and both count for TTFT/decode.
                piece = (d.get("content") or "") + (d.get("reasoning_content") or "")
            elif "content" in j:
                piece = (j.get("content") or "") + (j.get("reasoning_content") or "")
            if piece:
                now = time.time()
                if t_first is None:
                    t_first = now
                t_last = now
                ntok += 1
                text.append(piece)
            if j.get("timings"):
                timings = j["timings"]
    t_end = time.time()
    return dict(t_send=t_send, t_first=t_first, t_last=t_last, t_end=t_end,
                stream_chunks=ntok, timings=timings, text="".join(text))


def sig3(x):
    """Three significant figures, no aggressive rounding."""
    if x is None or x == "":
        return ""
    if x == 0:
        return "0.00"
    return f"{float(f'{float(x):.3g}'):g}"
