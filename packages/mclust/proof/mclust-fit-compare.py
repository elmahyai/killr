"""Compare the R and Python proofs of Mclust and densityMclust (mclust 6.1.3).

Run from packages/mclust after both proofs:
    Rscript proof/Mclust-r.R && .venv/bin/python proof/Mclust-py.py
    Rscript proof/densityMclust-r.R && .venv/bin/python proof/densityMclust-py.py
    .venv/bin/python proof/mclust-fit-compare.py

Reads docs/output/<name>-r.txt and docs/output/<name>-py.txt. Each line is a
record: a key, then tab-separated values. Numbers are compared with
|R - Python| <= 1e-8, with NA equal to NA; strings must be equal; the
time_ms line is not compared. Writes docs/output/mclust-fit-compare.txt.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

TOL = 1e-8
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "output"
FUNCTIONS = ["Mclust", "densityMclust"]


def _read(path: Path) -> tuple[list[list[str]], float]:
    records: list[list[str]] = []
    time_ms = float("nan")
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if parts[0] == "time_ms":
            time_ms = float(parts[1])
            continue
        records.append(parts)
    return records, time_ms


def _num(token: str):
    if token == "NA":
        return math.nan
    try:
        return float(token)
    except ValueError:
        return None


def compare(name: str) -> dict:
    missing = [p.name for p in (OUT / f"{name}-r.txt", OUT / f"{name}-py.txt") if not p.exists()]
    if missing:
        return {"name": name, "matches": False, "max_abs_diff": math.inf,
                "problems": [f"missing output: {', '.join(missing)}"],
                "r_ms": math.nan, "translated_ms": math.nan, "speedup": math.nan}
    r_recs, r_ms = _read(OUT / f"{name}-r.txt")
    p_recs, p_ms = _read(OUT / f"{name}-py.txt")
    result = {"name": name, "matches": True, "max_abs_diff": 0.0, "problems": [],
              "r_ms": r_ms, "translated_ms": p_ms,
              "speedup": r_ms / p_ms if p_ms > 0 else math.nan}
    if len(r_recs) != len(p_recs):
        result["matches"] = False
        result["problems"].append(f"record count R={len(r_recs)} Python={len(p_recs)}")
        result["max_abs_diff"] = math.inf
        return result
    for rr, pp in zip(r_recs, p_recs):
        if rr[0] != pp[0] or len(rr) != len(pp):
            result["matches"] = False
            result["problems"].append(f"key or length differs at {rr[0]}")
            continue
        for a, b in zip(rr[1:], pp[1:]):
            x, y = _num(a), _num(b)
            if x is None or y is None:
                if a != b:
                    result["matches"] = False
                    result["problems"].append(f"{rr[0]}: {a!r} != {b!r}")
                continue
            if math.isnan(x) or math.isnan(y):
                if math.isnan(x) != math.isnan(y):
                    result["matches"] = False
                    result["problems"].append(f"{rr[0]}: NA mismatch")
                    result["max_abs_diff"] = math.inf
                continue
            diff = abs(x - y)
            result["max_abs_diff"] = max(result["max_abs_diff"], diff)
            if diff > TOL:
                result["matches"] = False
                result["problems"].append(f"{rr[0]}: {x!r} vs {y!r}")
    return result


def main() -> int:
    lines = []
    all_ok = True
    for name in FUNCTIONS:
        res = compare(name)
        all_ok = all_ok and res["matches"]
        lines += [
            f"{name}",
            f"  matches: {'yes' if res['matches'] else 'no'}",
            f"  max_abs_diff: {res['max_abs_diff']:.3g}",
            f"  r_ms: {res['r_ms']:.3f}",
            f"  translated_ms: {res['translated_ms']:.3f}",
            f"  speedup: {res['speedup']:.3f}",
        ]
        lines += [f"  problem: {p}" for p in res["problems"][:20]]
        lines.append("")
    text = "\n".join(lines) + "\n"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "mclust-fit-compare.txt").write_text(text)
    print(text, end="")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
