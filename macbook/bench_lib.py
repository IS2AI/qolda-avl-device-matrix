"""Shared helpers for the Qolda-AVL-5B deployment benchmark (Device 2, Apple M4 Pro)."""
import base64, json, os, re, subprocess, threading, time
import urllib.request, urllib.error

BIN  = os.path.abspath("llama.cpp/build/bin")
ROOT = os.path.abspath(".")
HOST, PORT = "127.0.0.1", 8077
BASE = f"http://{HOST}:{PORT}"

POWER_LOG = os.path.join(ROOT, "power.log")

# ---------------------------------------------------------------- prompts
def parse_prompts(path="prompts_text.txt"):
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

# ---------------------------------------------------------------- vm_stat
def vm_stat():
    out = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
    d = {}
    for line in out.splitlines():
        m = re.match(r'"?([A-Za-z][^:"]*)"?:\s+(\d+)', line.strip())
        if m:
            d[m.group(1).strip()] = int(m.group(2))
    return d

def vm_delta(a, b):
    keys = ["Compressions", "Decompressions", "Swapins", "Swapouts",
            "Pages stored in compressor", "Pages occupied by compressor"]
    return {k: b.get(k, 0) - a.get(k, 0) for k in keys if k in a or k in b}

# ---------------------------------------------------------------- power
_PM_TS = re.compile(r"\*\*\* Sampled system activity \((.+?)\) \(([\d.]+)ms elapsed\)")
_PM_CPU = re.compile(r"^CPU Power:\s+([\d.]+)\s*mW", re.M)
_PM_GPU = re.compile(r"^GPU Power:\s+([\d.]+)\s*mW", re.M)

def parse_power_log(path=POWER_LOG):
    """Return [(epoch_seconds, cpu_w+gpu_w), ...] parsed from a powermetrics log."""
    if not os.path.exists(path):
        return []
    txt = open(path, errors="replace").read()
    blocks = re.split(r"(?=\*\*\* Sampled system activity)", txt)
    samples = []
    for b in blocks:
        mt = _PM_TS.search(b)
        if not mt:
            continue
        try:
            ts = time.mktime(time.strptime(mt.group(1).split(" +")[0].split(" -")[0].strip(),
                                           "%a %b %d %H:%M:%S %Y"))
        except ValueError:
            continue
        mc, mg = _PM_CPU.search(b), _PM_GPU.search(b)
        if mc and mg:
            samples.append((ts, (float(mc.group(1)) + float(mg.group(1))) / 1000.0))
    return samples

def mean_power_in_window(samples, t0, t1):
    w = [p for ts, p in samples if t0 - 0.2 <= ts <= t1 + 0.2]
    return (sum(w) / len(w)) if w else None

# ---------------------------------------------------------------- memory
def rss_kb(pid):
    try:
        o = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)],
                           capture_output=True, text=True).stdout.strip()
        return int(o) if o else None
    except Exception:
        return None

def footprint_bytes(pid):
    try:
        o = subprocess.run(["footprint", "-p", str(pid)],
                           capture_output=True, text=True, timeout=20).stdout
        m = re.search(r"Footprint:\s+([\d.]+)\s*(KB|MB|GB)", o)
        if not m:
            return None
        v, u = float(m.group(1)), m.group(2)
        return int(v * {"KB": 1024, "MB": 1024**2, "GB": 1024**3}[u])
    except Exception:
        return None

class MemSampler(threading.Thread):
    """Samples RSS of `pid` every `interval` s; records peak over the window."""
    def __init__(self, pid, interval=0.2):
        super().__init__(daemon=True)
        self.pid, self.interval = pid, interval
        self.peak_kb, self.n = 0, 0
        self._stop = threading.Event()
    def run(self):
        while not self._stop.is_set():
            v = rss_kb(self.pid)
            if v:
                self.peak_kb = max(self.peak_kb, v); self.n += 1
            self._stop.wait(self.interval)
    def stop(self):
        self._stop.set(); self.join(timeout=3)
        return self.peak_kb

# ---------------------------------------------------------------- server
class Server:
    def __init__(self, model, mmproj, log_path, extra=None, ctx=4096):
        self.model, self.mmproj, self.log_path = model, mmproj, log_path
        self.extra, self.ctx = extra or [], ctx
        self.proc = None
    def cmd(self):
        c = [f"{BIN}/llama-server", "-m", self.model,
             "--host", HOST, "--port", str(PORT),
             "-ngl", "999", "-c", str(self.ctx), "-b", "2048", "-ub", "512",
             "--no-mmap", "--parallel", "1", "--no-webui",
             "--reasoning-format", "none"]
        if self.mmproj:
            c += ["--mmproj", self.mmproj]
        return c + self.extra
    def start(self, timeout=600):
        self.log = open(self.log_path, "w")
        self.proc = subprocess.Popen(self.cmd(), stdout=self.log,
                                     stderr=subprocess.STDOUT)
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.proc.poll() is not None:
                raise RuntimeError(f"server exited rc={self.proc.returncode}\n"
                                   f"{tail(self.log_path, 40)}")
            try:
                with urllib.request.urlopen(f"{BASE}/health", timeout=2) as r:
                    if r.status == 200:
                        return time.time() - t0
            except Exception:
                time.sleep(0.5)
        raise RuntimeError(f"server not ready in {timeout}s\n{tail(self.log_path, 40)}")
    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.proc.kill(); self.proc.wait(timeout=10)
        try:
            self.log.close()
        except Exception:
            pass
        time.sleep(1.5)

def tail(p, n=30):
    try:
        return "\n".join(open(p, errors="replace").read().splitlines()[-n:])
    except Exception:
        return "<no log>"

# ---------------------------------------------------------------- requests
GEN = dict(n_predict=256, temperature=0.7, top_p=0.95, top_k=20,
           seed=1234, ignore_eos=True, cache_prompt=False, stream=True)

def build_body(mode, prompts, chat=True):
    """Returns (endpoint, body)."""
    if mode.startswith("text"):
        key = {"text-128": "<<<PROMPT_128>>>", "text-512": "<<<PROMPT_512>>>",
               "text-2048": "<<<PROMPT_2048>>>"}[mode]
        b = dict(GEN); b["prompt"] = prompts[key]
        return "/completion", b
    if mode == "vision":
        content = [
            {"type": "image_url",
             "image_url": {"url": "data:image/jpeg;base64," + b64file("bench_image.jpg")}},
            {"type": "text", "text": VISION_INSTR},
        ]
    elif mode.startswith("audio"):
        wav = "bench_audio_30s.wav" if mode == "audio-30s" else "bench_audio_10s.wav"
        content = [
            {"type": "input_audio",
             "input_audio": {"data": b64file(wav), "format": "wav"}},
            {"type": "text", "text": AUDIO_INSTR},
        ]
    else:
        raise ValueError(mode)
    b = dict(GEN); b.pop("n_predict")
    b.update(max_tokens=256, messages=[{"role": "user", "content": content}])
    return "/v1/chat/completions", b

VISION_INSTR = ("Суреттегі нысандарды, олардың өзара орналасуын, "
                "түстері мен көрінетін жазуларды егжей-тегжейлі сипаттап бер.")
AUDIO_INSTR  = "Аудиодағы сөйлеуді сөзбе-сөз жазып шық."

def stream_request(endpoint, body, timeout=1800):
    """Issue a streaming request; return timing dict."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + endpoint, data=data,
                                 headers={"Content-Type": "application/json"})
    t_send = time.time()
    t_first = None; t_last = None; ntok = 0; timings = None; text = []
    with urllib.request.urlopen(req, timeout=timeout) as r:
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
                t_last = now; ntok += 1; text.append(piece)
            if j.get("timings"):
                timings = j["timings"]
    t_end = time.time()
    return dict(t_send=t_send, t_first=t_first, t_last=t_last, t_end=t_end,
                stream_chunks=ntok, timings=timings, text="".join(text))
