"""
Qolda-AVL-5B-GGUF benchmark harness -- Device 1 (Windows / RTX 4090 Mobile, CUDA)
"""
import base64
import csv
import json
import subprocess
import threading
import time
from pathlib import Path

import psutil
import requests

ROOT = Path(__file__).parent
MODELS = ROOT / "models"
LLAMA_SERVER = Path("C:/qolda-bench/llama.cpp/build/bin/Release/llama-server.exe")
HOST = "127.0.0.1"
PORT = 8080
BASE_URL = f"http://{HOST}:{PORT}"

LLAMACPP_COMMIT = "ea63b4d32ea1b66bdbe369be7f9443f6c00f8b31"
DEVICE_CLASS = "discrete-gpu-laptop"
DEVICE_NAME = "RTX 4090 Laptop GPU (ASUS ROG, 16GB VRAM)"
BACKEND = "CUDA"

N_PREDICT = 256
GEN_KW = dict(temperature=0.7, top_p=0.95, top_k=20, seed=1234, ignore_eos=True, cache_prompt=False)
N_CTX = 4096
N_REPS = 5
N_WARMUP = 3
THERMAL_SOAK_SEC = 180

VARIANTS = [
    ("BF16", MODELS / "BF16" / "Qolda-AVL-5B-BF16.gguf"),
    ("Q8_0", MODELS / "Q8_0" / "Qolda-AVL-5B-Q8_0.gguf"),
    ("Q6_K", MODELS / "Q6_K" / "Qolda-AVL-5B-Q6_K.gguf"),
    ("Q5_K_M", MODELS / "Q5_K_M" / "Qolda-AVL-5B-Q5_K_M.gguf"),
    ("Q4_K_M", MODELS / "Q4_K_M" / "Qolda-AVL-5B-Q4_K_M.gguf"),
]
MMPROJ_AV = MODELS / "mmproj" / "mmproj-Qolda-AVL-5B-F16.gguf"
MMPROJ_VISION_ONLY = MODELS / "mmproj" / "mmproj-Qolda-AVL-5B-vision-only-F16.gguf"

VISION_INSTRUCTION = "Суреттегі нысандарды, олардың өзара орналасуын, түстері мен көрінетін жазуларды егжей-тегжейлі сипаттап бер."
AUDIO_INSTRUCTION = "Аудиодағы сөйлеуді сөзбе-сөз жазып шық."

IMAGE_PATH = ROOT / "bench_image.jpg"
AUDIO_30S_PATH = ROOT / "bench_audio_30s.wav"
AUDIO_10S_PATH = ROOT / "bench_audio_10s.wav"
PROMPTS_PATH = ROOT / "prompts_text.txt"

CSV_PATH = ROOT / "results.csv"
CSV_COLUMNS = [
    "device_class", "device_name", "backend", "llamacpp_commit", "patch_applied",
    "variant", "mmproj_variant", "mode", "prompt_tokens", "image_tokens",
    "audio_tokens", "audio_seconds", "gen_tokens", "run_idx", "thermal_state",
    "ttft_ms", "encoder_ms", "prefill_tps", "decode_tps", "total_ms",
    "peak_rss_gb", "peak_vram_gb", "avg_power_w", "idle_power_w",
    "energy_j_per_1k_tok", "notes",
]

LOG_PATH = ROOT / "bench_log.txt"


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def parse_prompts(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").split("\n")
    markers = [i for i, l in enumerate(lines) if l.startswith("<<<PROMPT_")]
    prompts = {}
    for idx, mi in enumerate(markers):
        name = lines[mi].strip()
        start = mi + 1
        end = markers[idx + 1] if idx + 1 < len(markers) else len(lines)
        body = "\n".join(lines[start:end]).rstrip()
        prompts[name] = body
    assert len(prompts) == 3, f"expected 3 prompts, got {len(prompts)}"
    for k, v in prompts.items():
        assert v.strip(), f"empty prompt body for {k}"
    return prompts


def b64_file(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


PROMPTS = parse_prompts(PROMPTS_PATH)
IMAGE_B64 = b64_file(IMAGE_PATH)
AUDIO_30S_B64 = b64_file(AUDIO_30S_PATH)
AUDIO_10S_B64 = b64_file(AUDIO_10S_PATH)


def build_payload(mode: str) -> dict:
    if mode == "text-128":
        content = PROMPTS["<<<PROMPT_128>>>"]
    elif mode == "text-512":
        content = PROMPTS["<<<PROMPT_512>>>"]
    elif mode == "text-2048":
        content = PROMPTS["<<<PROMPT_2048>>>"]
    elif mode == "vision":
        content = [
            {"type": "text", "text": VISION_INSTRUCTION},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{IMAGE_B64}"}},
        ]
    elif mode == "audio-30s":
        content = [
            {"type": "text", "text": AUDIO_INSTRUCTION},
            {"type": "input_audio", "input_audio": {"data": AUDIO_30S_B64, "format": "wav"}},
        ]
    elif mode == "audio-10s":
        content = [
            {"type": "text", "text": AUDIO_INSTRUCTION},
            {"type": "input_audio", "input_audio": {"data": AUDIO_10S_B64, "format": "wav"}},
        ]
    else:
        raise ValueError(mode)
    return {
        "messages": [{"role": "user", "content": content}],
        "n_predict": N_PREDICT,
        "stream": True,
        **GEN_KW,
    }


class ServerProcess:
    def __init__(self, model_path: Path, mmproj_path, n_gpu_layers=999, n_ctx=N_CTX):
        self.model_path = model_path
        self.mmproj_path = mmproj_path
        self.n_gpu_layers = n_gpu_layers
        self.n_ctx = n_ctx
        self.proc = None
        self.log_file = None

    def start(self, log_path: Path):
        cmd = [
            str(LLAMA_SERVER),
            "-m", str(self.model_path),
            "-ngl", str(self.n_gpu_layers),
            "-c", str(self.n_ctx),
            "--parallel", "1",
            "--host", HOST,
            "--port", str(PORT),
        ]
        if self.mmproj_path is not None:
            cmd += ["--mmproj", str(self.mmproj_path)]
        self.log_file = open(log_path, "w", encoding="utf-8")
        self.proc = subprocess.Popen(cmd, stdout=self.log_file, stderr=subprocess.STDOUT, text=True)
        self._wait_ready()

    def _wait_ready(self, timeout=300):
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                r = requests.get(f"{BASE_URL}/health", timeout=2)
                if r.status_code == 200:
                    return
            except requests.exceptions.ConnectionError:
                pass
            if self.proc.poll() is not None:
                raise RuntimeError(f"llama-server exited early with code {self.proc.returncode}, see log")
            time.sleep(0.5)
        raise TimeoutError("llama-server did not become ready in time")

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        if self.log_file:
            self.log_file.close()
        time.sleep(1)


def nvidia_smi_query(fields):
    out = subprocess.run(
        ["nvidia-smi", f"--query-gpu={fields}", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, timeout=5,
    )
    return out.stdout.strip()


class ResourceSampler:
    """Samples VRAM (nvidia-smi) + host RSS (psutil) + GPU power at 200ms."""

    def __init__(self, server_pid: int, interval=0.2):
        self.server_pid = server_pid
        self.interval = interval
        self._stop = threading.Event()
        self._thread = None
        self.vram_mib = []
        self.power_w = []
        self.rss_gb = []

    def _run(self):
        try:
            proc = psutil.Process(self.server_pid)
        except psutil.NoSuchProcess:
            proc = None
        while not self._stop.is_set():
            try:
                out = nvidia_smi_query("memory.used,power.draw")
                mem_str, pow_str = out.split(",")
                self.vram_mib.append(float(mem_str.strip()))
                self.power_w.append(float(pow_str.strip()))
            except Exception:
                pass
            if proc is not None:
                try:
                    rss = proc.memory_info().rss
                    for child in proc.children(recursive=True):
                        try:
                            rss += child.memory_info().rss
                        except Exception:
                            pass
                    self.rss_gb.append(rss / (1024 ** 3))
                except Exception:
                    pass
            time.sleep(self.interval)

    def start(self):
        self._stop.clear()
        self.vram_mib.clear()
        self.power_w.clear()
        self.rss_gb.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)

    def peak_vram_gb(self):
        return max(self.vram_mib) / 1024 if self.vram_mib else None

    def mean_power_w(self):
        return sum(self.power_w) / len(self.power_w) if self.power_w else None

    def peak_rss_gb(self):
        return max(self.rss_gb) if self.rss_gb else None


def idle_baseline(seconds=60, interval=0.5):
    log(f"measuring {seconds}s idle baseline...")
    samples = []
    t0 = time.time()
    while time.time() - t0 < seconds:
        try:
            out = nvidia_smi_query("power.draw")
            samples.append(float(out.strip()))
        except Exception:
            pass
        time.sleep(interval)
    mean_p = sum(samples) / len(samples) if samples else None
    log(f"idle baseline: {mean_p:.2f} W (n={len(samples)})")
    return mean_p


def gpu_temp():
    try:
        return float(nvidia_smi_query("temperature.gpu"))
    except Exception:
        return None


def do_request(payload):
    """Send one streamed chat completion; return dict of measured metrics or raises."""
    t_send = time.time()
    r = requests.post(f"{BASE_URL}/v1/chat/completions", json=payload, stream=True, timeout=180)
    r.raise_for_status()
    t_first_content = None
    t_first_chunk = None
    t_last_chunk = None
    final_timings = None
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        data = line[len("data:"):].strip()
        if data == "[DONE]":
            break
        now = time.time()
        if t_first_chunk is None:
            t_first_chunk = now
        try:
            obj = json.loads(data)
        except json.JSONDecodeError:
            continue
        choice = obj.get("choices", [{}])[0]
        delta = choice.get("delta", {})
        has_content = bool(delta.get("content") or delta.get("reasoning_content"))
        if has_content and t_first_content is None:
            t_first_content = now
        if "timings" in obj:
            final_timings = obj["timings"]
            t_last_chunk = now
    if t_last_chunk is None:
        t_last_chunk = time.time()
    if final_timings is None:
        raise RuntimeError("no timings object received in stream")

    ttft_ms = ((t_first_content or t_first_chunk or t_last_chunk) - t_send) * 1000
    predicted_n = final_timings.get("predicted_n", 0)
    prompt_n = final_timings.get("prompt_n", 0)
    prompt_ms = final_timings.get("prompt_ms", 0.0)
    predicted_ms = final_timings.get("predicted_ms", 0.0)

    decode_tps = None
    if t_first_content is not None and t_last_chunk > t_first_content and predicted_n > 1:
        decode_tps = (predicted_n - 1) / (t_last_chunk - t_first_content)

    prefill_tps = (prompt_n / (prompt_ms / 1000.0)) if prompt_ms else None
    total_ms = (t_last_chunk - t_send) * 1000

    return dict(
        ttft_ms=ttft_ms, prefill_tps=prefill_tps, decode_tps=decode_tps, total_ms=total_ms,
        prompt_n=prompt_n, predicted_n=predicted_n, prompt_ms=prompt_ms, predicted_ms=predicted_ms,
    )


def run_cell(variant, mmproj_variant, mode, sampler: ResourceSampler, idle_power, rows: list, notes_extra=""):
    payload = build_payload(mode)
    for run_idx in range(1, N_REPS + 1):
        sampler.start()
        try:
            m = do_request(payload)
            err = None
        except Exception as e:
            m = None
            err = str(e)
        sampler.stop()

        if m is None:
            row = {c: "" for c in CSV_COLUMNS}
            row.update(dict(
                device_class=DEVICE_CLASS, device_name=DEVICE_NAME, backend=BACKEND,
                llamacpp_commit=LLAMACPP_COMMIT, patch_applied="yes",
                variant=variant, mmproj_variant=mmproj_variant, mode=mode,
                run_idx=run_idx, thermal_state="sustained",
                notes=(f"FAILED: {err}" + (f"; {notes_extra}" if notes_extra else "")),
            ))
            rows.append(row)
            log(f"  run {run_idx}: FAILED: {err}")
            continue

        avg_power = sampler.mean_power_w()
        peak_vram = sampler.peak_vram_gb()
        peak_rss = sampler.peak_rss_gb()
        decode_seconds = m["predicted_ms"] / 1000.0
        energy = None
        if avg_power is not None and idle_power is not None and m["predicted_n"] > 0 and decode_seconds > 0:
            energy = (avg_power - idle_power) * decode_seconds / m["predicted_n"] * 1000

        image_tokens = ""
        audio_tokens = ""
        audio_seconds = ""
        if mode == "vision":
            image_tokens = max(m["prompt_n"] - 65, 0)
        elif mode == "audio-30s":
            audio_tokens = max(m["prompt_n"] - 28, 0)
            audio_seconds = 30
        elif mode == "audio-10s":
            audio_tokens = max(m["prompt_n"] - 28, 0)
            audio_seconds = 10

        rows.append(dict(
            device_class=DEVICE_CLASS, device_name=DEVICE_NAME, backend=BACKEND,
            llamacpp_commit=LLAMACPP_COMMIT, patch_applied="yes",
            variant=variant, mmproj_variant=mmproj_variant, mode=mode,
            prompt_tokens=m["prompt_n"], image_tokens=image_tokens, audio_tokens=audio_tokens,
            audio_seconds=audio_seconds, gen_tokens=m["predicted_n"], run_idx=run_idx,
            thermal_state="sustained",
            ttft_ms=round(m["ttft_ms"], 3),
            encoder_ms="",
            prefill_tps=round(m["prefill_tps"], 3) if m["prefill_tps"] else "",
            decode_tps=round(m["decode_tps"], 3) if m["decode_tps"] else "",
            total_ms=round(m["total_ms"], 3),
            peak_rss_gb=round(peak_rss, 4) if peak_rss else "",
            peak_vram_gb=round(peak_vram, 4) if peak_vram else "",
            avg_power_w=round(avg_power, 3) if avg_power else "",
            idle_power_w=round(idle_power, 3) if idle_power else "",
            energy_j_per_1k_tok=round(energy, 3) if energy is not None else "",
            notes=notes_extra,
        ))
        log(f"  run {run_idx}: ttft={m['ttft_ms']:.1f}ms decode_tps={m['decode_tps']:.2f} "
            f"prefill_tps={m['prefill_tps']:.1f} prompt_n={m['prompt_n']} gen={m['predicted_n']}")


def thermal_soak(seconds=THERMAL_SOAK_SEC):
    log(f"thermal soak: generating continuously for {seconds}s...")
    t0 = time.time()
    payload = build_payload("text-512")
    n = 0
    while time.time() - t0 < seconds:
        try:
            do_request(payload)
            n += 1
        except Exception as e:
            log(f"  soak request failed: {e}")
    log(f"thermal soak done ({n} requests, {time.time()-t0:.0f}s)")


MODES = ["text-128", "text-512", "text-2048", "vision", "audio-30s", "audio-10s"]


def _write_csv(rows):
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for row in rows:
            w.writerow({c: row.get(c, "") for c in CSV_COLUMNS})


def main():
    rows = []
    log("=== Qolda-AVL-5B-GGUF benchmark: Device 1 (Windows/RTX4090 Mobile/CUDA) ===")

    idle_before = idle_baseline(60)

    for variant, model_path in VARIANTS:
        log(f"=== variant {variant} ===")
        temp_start = gpu_temp()
        srv = ServerProcess(model_path, MMPROJ_AV)
        srv.start(ROOT / f"server_{variant}.log")
        log(f"server started for {variant}, pid={srv.proc.pid}")

        thermal_soak()

        sampler = ResourceSampler(srv.proc.pid)
        for _ in range(N_WARMUP):
            try:
                do_request(build_payload("text-128"))
            except Exception as e:
                log(f"warmup failed: {e}")

        for mode in MODES:
            log(f"-- {variant} / audio+vision / {mode} --")
            run_cell(variant, "audio+vision", mode, sampler, idle_before, rows)
            _write_csv(rows)

        temp_end = gpu_temp()
        log(f"variant {variant} done. GPU temp start={temp_start}C end={temp_end}C")
        srv.stop()

        if variant == "Q4_K_M":
            log("=== control (a): Q4_K_M, no mmproj, text-512 ===")
            srv_a = ServerProcess(model_path, None)
            srv_a.start(ROOT / "server_Q4_K_M_control_a.log")
            sampler_a = ResourceSampler(srv_a.proc.pid)
            for _ in range(N_WARMUP):
                try:
                    do_request(build_payload("text-128"))
                except Exception as e:
                    log(f"warmup failed: {e}")
            run_cell("Q4_K_M", "none", "text-512", sampler_a, idle_before, rows,
                     notes_extra="control (a): isolates projector memory cost")
            _write_csv(rows)
            srv_a.stop()

            log("=== control (b): Q4_K_M, vision-only mmproj, vision ===")
            srv_b = ServerProcess(model_path, MMPROJ_VISION_ONLY)
            srv_b.start(ROOT / "server_Q4_K_M_control_b.log")
            sampler_b = ResourceSampler(srv_b.proc.pid)
            for _ in range(N_WARMUP):
                try:
                    do_request(build_payload("text-128"))
                except Exception as e:
                    log(f"warmup failed: {e}")
            run_cell("Q4_K_M", "vision-only", "vision", sampler_b, idle_before, rows,
                     notes_extra="control (b): quantifies audio-branch memory penalty")
            _write_csv(rows)
            srv_b.stop()

    idle_after = idle_baseline(60)
    log(f"idle power before={idle_before:.2f}W after={idle_after:.2f}W")

    _write_csv(rows)
    log(f"DONE. wrote {len(rows)} rows to {CSV_PATH}")


if __name__ == "__main__":
    main()
