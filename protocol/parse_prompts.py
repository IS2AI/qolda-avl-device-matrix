import re, sys, hashlib

def parse(path="prompts_text.txt"):
    raw = open(path, encoding="utf-8").read()
    lines = raw.split("\n")
    marks = [(i, l.strip()) for i, l in enumerate(lines)
             if l.startswith("<<<PROMPT_")]
    out = {}
    for k, (i, name) in enumerate(marks):
        end = marks[k+1][0] if k+1 < len(marks) else len(lines)
        body = "\n".join(lines[i+1:end]).rstrip()
        out[name] = body
    return out

if __name__ == "__main__":
    p = parse()
    print(f"markers found: {len(p)}")
    for k, v in p.items():
        nonempty = "OK" if v.strip() else "EMPTY"
        print(f"{k:22} chars={len(v):6d} words={len(v.split()):5d} {nonempty} "
              f"sha12={hashlib.sha256(v.encode()).hexdigest()[:12]}")
        print(f"    head: {v[:70]!r}")
        print(f"    tail: {v[-70:]!r}")
    ne = [v for v in p.values() if v.strip()]
    print(f"\nnon-empty prompts recovered: {len(ne)}")
    assert len(ne) == 3, f"EXPECTED 3, GOT {len(ne)}"
    print("PARSE OK")
