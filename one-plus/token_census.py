#!/usr/bin/env python3
"""One-off token census for Device 3, recorded once and reported in summary.md.

Text prompts and the two fixed instructions are counted with llama-tokenize
--no-bos on the patched ea63b4d build (the prompt file was generated with a
Homebrew build, so this is also the tokenizer cross-check).

Image and audio token counts come from the server's own reported prompt_n for a
1-token generation in each modality, minus the text-only baseline for the same
instruction, which isolates what the projector contributed.
"""
import json, os, re, subprocess, sys, time
import bench_lib as B

MODEL = "models/Q4_K_M/Qolda-AVL-5B-Q4_K_M.gguf"
OUT = os.path.join(B.ROOT, "token_census.json")
DEV_TMP = f"{B.DEV_ROOT}/art"


def tokenize_file(dev_path):
    """Run llama-tokenize --no-bos on a file already on the device.

    Counting happens on the device: llama-tokenize prints one `<id> -> '<piece>'`
    line per token, and a 2048-token prompt would otherwise ship every line back
    over adb. Do NOT truncate the output before counting.
    """
    cmd = (f"cd {B.DEV_ROOT} && LD_LIBRARY_PATH={B.DEV_BIN} "
           f"{B.DEV_BIN}/llama-tokenize -m {B.DEV_ROOT}/{MODEL} "
           f"--no-bos -f {dev_path} 2>/dev/null "
           f"| grep -cE \"^ *[0-9]+ -> \"")
    out = B.sh(cmd, timeout=900).stdout.strip()
    m = re.search(r"(\d+)", out)
    return int(m.group(1)) if m else None


def tokenize_text(text, name):
    """Write text to the device and tokenize it."""
    local = os.path.join("/tmp", f"tok_{name}.txt")
    open(local, "w", encoding="utf-8").write(text)
    B.adb("push", local, f"{DEV_TMP}/tok_{name}.txt", timeout=60)
    n = tokenize_file(f"{DEV_TMP}/tok_{name}.txt")
    B.sh(f"rm -f {DEV_TMP}/tok_{name}.txt")
    return n


def probe_prompt_n(server, mode, prompts):
    """Issue a 1-token request and read prompt_n from the server timings."""
    ep, body = B.build_body(mode, prompts)
    if "n_predict" in body:
        body["n_predict"] = 1
    else:
        body["max_tokens"] = 1
    r = B.stream_request(ep, body, timeout=3600)
    tim = r.get("timings") or {}
    return tim.get("prompt_n"), tim


def main():
    prompts = B.parse_prompts()
    res = {"tokenizer": {}, "server_prompt_n": {}, "modes": {}}

    print("=== llama-tokenize --no-bos (patched ea63b4d, on device) ===", flush=True)
    for key, label, expected in [("<<<PROMPT_128>>>", "text-128", 128),
                                 ("<<<PROMPT_512>>>", "text-512", 513),
                                 ("<<<PROMPT_2048>>>", "text-2048", 2048)]:
        n = tokenize_text(prompts[key], label)
        res["tokenizer"][label] = n
        flag = "MATCH" if n == expected else f"DIVERGES (expected {expected})"
        print(f"  {label:<10} {n}  {flag}", flush=True)

    n_vis = tokenize_text(B.VISION_INSTR, "vision_instr")
    n_aud = tokenize_text(B.AUDIO_INSTR, "audio_instr")
    res["tokenizer"]["vision_instruction"] = n_vis
    res["tokenizer"]["audio_instruction"] = n_aud
    print(f"  vision instr {n_vis}  {'MATCH' if n_vis == 65 else 'DIVERGES (expected 65)'}",
          flush=True)
    print(f"  audio instr  {n_aud}  {'MATCH' if n_aud == 28 else 'DIVERGES (expected 28)'}",
          flush=True)

    print("\n=== server-reported prompt_n (Q4_K_M + audio+vision mmproj) ===",
          flush=True)
    srv = B.Server(MODEL, "models/mmproj/mmproj-Qolda-AVL-5B-F16.gguf",
                   "server_census.log", threads=6)
    srv.start()
    try:
        for mode in ["text-128", "text-512", "text-2048",
                     "vision", "audio-30s", "audio-10s"]:
            n, tim = probe_prompt_n(srv, mode, prompts)
            res["server_prompt_n"][mode] = n
            print(f"  {mode:<10} prompt_n={n}  prompt_ms={tim.get('prompt_ms')}",
                  flush=True)
    finally:
        srv.stop()

    # Derive modality token counts: total prompt_n minus the chat-wrapped
    # instruction. Reported as-is; the chat template overhead is stated in
    # summary.md rather than silently subtracted.
    res["modes"] = {
        "vision": dict(image_tokens=res["server_prompt_n"].get("vision"),
                       audio_tokens="", audio_seconds=""),
        "audio-30s": dict(image_tokens="",
                          audio_tokens=res["server_prompt_n"].get("audio-30s"),
                          audio_seconds="30.0"),
        "audio-10s": dict(image_tokens="",
                          audio_tokens=res["server_prompt_n"].get("audio-10s"),
                          audio_seconds="10.0"),
    }

    json.dump(res, open(OUT, "w"), indent=2, ensure_ascii=False)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
