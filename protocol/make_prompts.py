#!/usr/bin/env python3
"""Build fixed-token-length Kazakh benchmark prompts using llama-tokenize.

For each target length in TARGETS, finds a prefix of the source text such
that (prefix + INSTRUCTION) tokenizes to exactly `target` tokens (no BOS).
Writes all prompts to a single delimited output file.
"""

import argparse
import hashlib
import re
import subprocess
import sys
import tempfile
import os

TARGETS = [128, 512, 2048]

# Appended after the source-text context, turning a raw Wikipedia dump into
# an instruction-shaped query -- a fairer prefill workload than raw text.
INSTRUCTION = (
    "\n\nЖоғарыдағы мәтінді мұқият оқып шық. Осы мәтін негізінде басты "
    "оқиғаларды, адамдарды және фактілерді қазақ тілінде егжей-тегжейлі "
    "әрі құрылымды түрде тұжырымда."
)


def count_tokens(tokenizer, model, text):
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write(text)
        path = f.name
    try:
        cmd = [tokenizer, "-m", model, "-f", path, "--ids", "--no-bos"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        out = result.stdout.strip()
        m = re.search(r"\[[^\]]*\]", out, re.S)
        if not m:
            raise RuntimeError(f"Could not parse token ids from output:\n{out}\n{result.stderr}")
        ids_str = m.group(0)
        ids = [x for x in ids_str.strip("[]").split(",") if x.strip() != ""]
        return len(ids)
    finally:
        os.unlink(path)


def build_prompt(tokenizer, model, words, target, instruction):
    """Binary search over word count, then char count within the boundary
    word, to get as close to `target` tokens as possible (>= target,
    minimal overshoot) once whole-word granularity isn't exact."""

    def total_tokens(prefix_text):
        return count_tokens(tokenizer, model, prefix_text + instruction)

    lo, hi = 0, len(words)
    # find minimal word count n such that tokens(words[:n]) >= target
    while lo < hi:
        mid = (lo + hi) // 2
        text = " ".join(words[:mid])
        if total_tokens(text) >= target:
            hi = mid
        else:
            lo = mid + 1
    n = lo

    prefix_words = " ".join(words[:n])
    exact = total_tokens(prefix_words)
    if exact == target or n == 0:
        return prefix_words + instruction, exact

    base_words = " ".join(words[: n - 1])
    base_count = total_tokens(base_words)
    if base_count == target:
        return base_words + instruction, base_count

    boundary_word = words[n - 1]
    clo, chi = 0, len(boundary_word)
    while clo < chi:
        cmid = (clo + chi) // 2
        candidate = base_words + (" " if base_words else "") + boundary_word[:cmid]
        if total_tokens(candidate) >= target:
            chi = cmid
        else:
            clo = cmid + 1

    candidate = base_words + (" " if base_words else "") + boundary_word[:clo]
    actual = total_tokens(candidate)
    return candidate + instruction, actual


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    source_text = open(args.source, encoding="utf-8").read()
    words = source_text.split()

    instr_tokens = count_tokens(args.tokenizer, args.model, INSTRUCTION)
    print(f"Instruction suffix: {instr_tokens} tokens")

    entries = []
    ok = True
    for target in TARGETS:
        prompt, actual = build_prompt(args.tokenizer, args.model, words, target, INSTRUCTION)
        if actual == target:
            print(f"target {target:5d} -> actual {actual:5d}  [OK]")
        else:
            off = actual - target
            print(f"target {target:5d} -> actual {actual:5d}  [OFF BY {off}]")
            ok = False
        entries.append((target, prompt))

    with open(args.out, "w", encoding="utf-8") as f:
        for target, prompt in entries:
            f.write(f"<<<PROMPT_{target}>>>\n")
            f.write(prompt)
            f.write("\n")

    print(f"\nWrote {args.out}")
    sha256 = hashlib.sha256(open(args.out, "rb").read()).hexdigest()
    print(f"sha256: {sha256}")

    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
