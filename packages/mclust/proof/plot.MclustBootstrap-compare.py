"""Compare the R and Python proofs of plot.MclustBootstrap (mclust 6.1.3).

Run from packages/mclust after both plot proofs:
    Rscript proof/plot.MclustBootstrap-r.R
    /home/ahmed/killr_projects/killr/.venv/bin/python proof/plot.MclustBootstrap-py.py
    /home/ahmed/killr_projects/killr/.venv/bin/python proof/plot.MclustBootstrap-compare.py

Reads docs/output/plot.MclustBootstrap-r.txt and -py.txt. Each record line is
compared field by field: numbers with |R - Python| <= 1e-8 (NA equal to NA),
strings exactly, and the record count and order must match. The time_ms line
is not compared. Writes docs/output/plot.MclustBootstrap-compare.txt.
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


def _num_tokens(field: str):
    toks = field.split(" ") if field else []
    out = []
    for t in toks:
        if t == "NA":
            out.append(math.nan)
        else:
            try:
                out.append(float(t))
            except ValueError:
                return None
    return out


def compare() -> dict:
    r_path = OUT / "plot.MclustBootstrap-r.txt"
    p_path = OUT / "plot.MclustBootstrap-py.txt"
    missing = [p.name for p in (r_path, p_path) if not p.exists()]
    if missing:
        return {"matches": False, "max_abs_diff": math.inf, "values": 0,
                "problems": [f"missing output: {', '.join(missing)}"],
                "r_ms": math.nan, "translated_ms": math.nan, "speedup": math.nan,
                "records": 0, "cases": 0}
    r_recs, r_ms = _read(r_path)
    p_recs, p_ms = _read(p_path)
    res = {"matches": True, "max_abs_diff": 0.0, "values": 0, "problems": [],
           "r_ms": r_ms, "translated_ms": p_ms,
           "speedup": r_ms / p_ms if p_ms > 0 else math.nan,
           "records": len(r_recs), "cases": sum(1 for r in r_recs if r[0].startswith("CASE "))}
    if len(r_recs) != len(p_recs):
        res["matches"] = False
        res["max_abs_diff"] = math.inf
        res["problems"].append(f"record count R={len(r_recs)} Python={len(p_recs)}")
        return res
    for i, (rr, pp) in enumerate(zip(r_recs, p_recs)):
        if rr[0] != pp[0] or len(rr) != len(pp):
            res["matches"] = False
            res["problems"].append(f"record {i}: tag or field count differs ({rr[0]} vs {pp[0]})")
            continue
        for a, b in zip(rr[1:], pp[1:]):
            if a == b:
                continue
            xa, xb = _num_tokens(a), _num_tokens(b)
            if xa is None or xb is None or len(xa) != len(xb):
                res["matches"] = False
                res["problems"].append(f"{rr[0]} record {i}: {a!r} vs {b!r}")
                continue
            for u, v in zip(xa, xb):
                if math.isnan(u) or math.isnan(v):
                    if math.isnan(u) != math.isnan(v):
                        res["matches"] = False
                        res["problems"].append(f"{rr[0]} record {i}: NA mismatch")
                    continue
                res["values"] += 1
                diff = abs(u - v)
                res["max_abs_diff"] = max(res["max_abs_diff"], diff)
                if diff > TOL:
                    res["matches"] = False
                    res["problems"].append(f"{rr[0]} record {i}: {u!r} vs {v!r}")
    return res


def main() -> int:
    res = compare()
    text = "\n".join([
        "plot.MclustBootstrap",
        f"  matches: {'yes' if res['matches'] else 'no'}",
        f"  max_abs_diff: {res['max_abs_diff']:.3g}",
        f"  cases: {res['cases']}",
        f"  records_compared: {res['records']}",
        f"  values_compared: {res['values']}",
        f"  r_ms: {res['r_ms']:.3f}",
        f"  translated_ms: {res['translated_ms']:.3f}",
        f"  speedup: {res['speedup']:.3f}",
        *[f"  problem: {p}" for p in res["problems"][:20]],
        "",
    ])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "plot.MclustBootstrap-compare.txt").write_text(text)
    print(text, end="")
    return 0 if res["matches"] else 1


if __name__ == "__main__":
    sys.exit(main())
