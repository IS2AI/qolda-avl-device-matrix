#!/usr/bin/env bash
# Check that the published data is internally consistent. Needs no model files,
# no llama.cpp build, and no benchmark run.
set -uo pipefail
cd "$(dirname "$0")"
fail=0

echo "== file hashes against MANIFEST.md =="
if shasum -a 256 -c <(awk -F'|' '/^\| `/ {gsub(/[` ]/,"",$2); gsub(/[` ]/,"",$5); print $5"  "$2}' MANIFEST.md) \
   | grep -v ": OK$"; then
  echo "  (lines above failed)"; fail=1
else
  echo "  all files match"
fi

echo
echo "== merged_results.csv re-derived from the three device CSVs =="
python3 tools/merge_results.py || fail=1

echo
echo "== the three devices ran the same commit =="
python3 - <<'PY'
import csv
r = list(csv.DictReader(open("merged_results.csv", encoding="utf-8")))
for k in ("llamacpp_commit", "patch_applied"):
    v = sorted({x[k] for x in r})
    print(f"  {k}: {v}")
    assert len(v) == 1, f"{k} differs across devices"
print(f"  rows: {len(r)}")
PY
[ $? -eq 0 ] || fail=1

exit $fail
