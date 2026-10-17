"""Compare the R and Python proofs of MclustBootstrap types wlbs, pb and jk (mclust 6.1.3).

Run from packages/mclust after both type proofs:
    Rscript proof/MclustBootstrap-types-r.R
    /home/ahmed/killr_projects/killr/.venv/bin/python proof/MclustBootstrap-types-py.py
    /home/ahmed/killr_projects/killr/.venv/bin/python proof/MclustBootstrap-types-compare.py

Reads docs/output/MclustBootstrap-types-r.txt and docs/output/MclustBootstrap-types-py.txt.
Numbers are compared with |R - Python| <= 1e-8, NA equal to NA, strings equal.
Records are grouped by type. Writes docs/output/MclustBootstrap-types-compare.txt.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

TOL = 1e-8
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "output"
TYPES = ("wlbs", "pb", "jk")


def _read(path: Path):
    records: list[list[str]] = []
    times: dict[str, float] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 3 and parts[1] == "time_ms":
            times[parts[0]] = float(parts[2])
            continue
        records.append(parts)
    return records, times


def _num(token: str):
    if token == "NA":
        return math.nan
    try:
        return float(token)
    except ValueError:
        return None


def _group(records: list[list[str]], type_: str) -> list[list[str]]:
    return [r for r in records if r[0] == type_]


def compare_type(r_recs, p_recs, type_: str) -> dict:
    result = {"type": type_, "matches": True, "max_abs_diff": 0.0, "problems": [],
              "values": 0, "nonfit": None}
    rr_list = _group(r_recs, type_)
    pp_list = _group(p_recs, type_)
    if len(rr_list) != len(pp_list) or not rr_list:
        result["matches"] = False
        result["problems"].append(f"record count R={len(rr_list)} Python={len(pp_list)}")
        result["max_abs_diff"] = math.inf
        return result
    for rr, pp in zip(rr_list, pp_list):
        if rr[0] != pp[0] or len(rr) != len(pp):
            result["matches"] = False
            result["problems"].append(f"key or length differs at {rr[:3]}")
            continue
        for a, b in zip(rr[1:], pp[1:]):
            x, y = _num(a), _num(b)
            if x is None or y is None:
                if a != b:
                    result["matches"] = False
                    result["problems"].append(f"{rr[:3]}: {a!r} != {b!r}")
                continue
            if math.isnan(x) or math.isnan(y):
                if math.isnan(x) != math.isnan(y):
                    result["matches"] = False
                    result["problems"].append(f"{rr[:3]}: NA mismatch")
                    result["max_abs_diff"] = math.inf
                continue
            result["values"] += 1
            diff = abs(x - y)
            result["max_abs_diff"] = max(result["max_abs_diff"], diff)
            if diff > TOL:
                result["matches"] = False
                result["problems"].append(f"{rr[:3]}: {x!r} vs {y!r}")
    return result


def compare() -> dict:
    r_path = OUT / "MclustBootstrap-types-r.txt"
    p_path = OUT / "MclustBootstrap-types-py.txt"
    missing = [p.name for p in (r_path, p_path) if not p.exists()]
    if missing:
        raise SystemExit(f"missing output: {', '.join(missing)}")
    r_recs, r_times = _read(r_path)
    p_recs, p_times = _read(p_path)
    results = {}
    for t in TYPES:
        res = compare_type(r_recs, p_recs, t)
        res["r_ms"] = r_times.get(t, math.nan)
        res["translated_ms"] = p_times.get(t, math.nan)
        res["speedup"] = (res["r_ms"] / res["translated_ms"]
                          if res["translated_ms"] > 0 else math.nan)
        results[t] = res
    return results


def main() -> int:
    results = compare()
    blocks = []
    all_ok = True
    for t in TYPES:
        res = results[t]
        all_ok = all_ok and res["matches"]
        blocks += [
            t,
            f"  matches: {'yes' if res['matches'] else 'no'}",
            f"  max_abs_diff: {res['max_abs_diff']:.3g}",
            f"  values_compared: {res['values']}",
            f"  r_ms: {res['r_ms']:.3f}",
            f"  translated_ms: {res['translated_ms']:.3f}",
            f"  speedup: {res['speedup']:.3f}",
            *[f"  problem: {p}" for p in res["problems"][:20]],
            "",
        ]
    text = "\n".join(blocks)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "MclustBootstrap-types-compare.txt").write_text(text + "\n")
    print(text)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
