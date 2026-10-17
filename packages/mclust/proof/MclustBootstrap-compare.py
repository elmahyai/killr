"""Compare the R and Python proofs of MclustBootstrap (mclust 6.1.3).

Run from packages/mclust after both proofs:
    Rscript proof/MclustBootstrap-r.R
    /home/ahmed/killr_projects/killr/.venv/bin/python proof/MclustBootstrap-py.py
    /home/ahmed/killr_projects/killr/.venv/bin/python proof/MclustBootstrap-compare.py

Reads docs/output/MclustBootstrap-r.txt and docs/output/MclustBootstrap-py.txt.
Numbers are compared with |R - Python| <= 1e-8, NA equal to NA, strings equal.
The time_ms line is not compared. Writes docs/output/MclustBootstrap-compare.txt.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

TOL = 1e-8
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "output"


def _read(path: Path) -> tuple[list[list[str]], float]:
    records: list[list[str]] = []
    time_ms = math.nan
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


def compare() -> dict:
    r_path = OUT / "MclustBootstrap-r.txt"
    p_path = OUT / "MclustBootstrap-py.txt"
    missing = [p.name for p in (r_path, p_path) if not p.exists()]
    if missing:
        return {"matches": False, "max_abs_diff": math.inf,
                "problems": [f"missing output: {', '.join(missing)}"],
                "r_ms": math.nan, "translated_ms": math.nan, "speedup": math.nan,
                "values": 0}
    r_recs, r_ms = _read(r_path)
    p_recs, p_ms = _read(p_path)
    result = {"matches": True, "max_abs_diff": 0.0, "problems": [],
              "r_ms": r_ms, "translated_ms": p_ms,
              "speedup": r_ms / p_ms if p_ms > 0 else math.nan, "values": 0}
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
            result["values"] += 1
            diff = abs(x - y)
            result["max_abs_diff"] = max(result["max_abs_diff"], diff)
            if diff > TOL:
                result["matches"] = False
                result["problems"].append(f"{rr[0]}: {x!r} vs {y!r}")
    return result


def main() -> int:
    res = compare()
    text = "\n".join([
        "MclustBootstrap",
        f"  matches: {'yes' if res['matches'] else 'no'}",
        f"  max_abs_diff: {res['max_abs_diff']:.3g}",
        f"  values_compared: {res['values']}",
        f"  r_ms: {res['r_ms']:.3f}",
        f"  translated_ms: {res['translated_ms']:.3f}",
        f"  speedup: {res['speedup']:.3f}",
        *[f"  problem: {p}" for p in res["problems"][:20]],
        "",
    ])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "MclustBootstrap-compare.txt").write_text(text)
    print(text, end="")
    return 0 if res["matches"] else 1


if __name__ == "__main__":
    sys.exit(main())
