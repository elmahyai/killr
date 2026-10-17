"""Shared inputs, timing, record I/O and comparison for the interp proofs.

Run after the matching R script, from packages/interp:
    Rscript proof/tri.mesh-r.R && python3 proof/tri.mesh-py.py
"""

import time
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[1] / "docs" / "output"
TOL = 1e-8


def lcg(n, seed):
    """Park-Miller minimal standard generator, the same integers as R."""
    out = np.empty(n, dtype=float)
    s = seed
    for i in range(n):
        s = (16807 * s) % 2147483647
        out[i] = s / 2147483647
    return out


def point_cases():
    s60 = lcg(120, 42)
    s200 = lcg(400, 7)
    s30 = lcg(60, 5)
    s40 = lcg(80, 99)
    x30 = s30[0:30]
    y30 = s30[30:60]
    idx = [1, 6, 10]  # R indices 2, 7, 11
    dx = x30[idx]
    dy = y30[idx]
    return [
        dict(id="rand60", x=s60[0:60], y=s60[60:120], dup="error"),
        dict(id="rand200", x=s200[0:200], y=s200[200:400], dup="error"),
        dict(
            id="grid5",
            x=np.tile(np.arange(1.0, 6.0), 5),
            y=np.repeat(np.arange(1.0, 6.0), 5),
            dup="error",
        ),
        dict(id="scaled40", x=s40[0:40] * 1000 - 500, y=s40[40:80] * 0.001, dup="error"),
        dict(id="dups-remove", x=np.concatenate([x30, dx]), y=np.concatenate([y30, dy]), dup="remove"),
        dict(id="dups-strip", x=np.concatenate([x30, dx]), y=np.concatenate([y30, dy]), dup="strip"),
        dict(id="quad4", x=np.array([0.0, 2.0, 1.0, 0.2]), y=np.array([0.0, 0.0, 1.5, 1.2]), dup="error"),
    ]


def canon_tri(trlist, cclist):
    """Sort vertices in each triangle, then sort the triangles lexicographically."""
    trlist = np.asarray(trlist)
    v = np.sort(trlist[:, 0:3], axis=1)
    o = np.lexsort((v[:, 2], v[:, 1], v[:, 0]))
    return v[o], np.asarray(cclist)[o]


def median_ms(f, reps=20):
    """Median of `reps` calls in milliseconds, from time.perf_counter()."""
    t = np.empty(reps)
    for k in range(reps):
        s = time.perf_counter()
        f()
        t[k] = (time.perf_counter() - s) * 1000.0
    return float(np.median(t))


def write_record(name, rec, py_ms):
    OUT.mkdir(parents=True, exist_ok=True)
    rec = dict(rec)
    rec["_py_median_ms"] = py_ms
    lines = []
    for k, v in rec.items():
        vals = np.asarray(v, dtype=float).ravel()
        lines.append(k + "\t" + " ".join("%.17g" % x for x in vals))
    (OUT / f"{name}-py.txt").write_text("\n".join(lines) + "\n")


def read_record(name):
    rec = {}
    for line in (OUT / f"{name}-r.txt").read_text().splitlines():
        key, _, rest = line.partition("\t")
        rec[key] = np.array([float(v) for v in rest.split()], dtype=float)
    return rec


def compare(py_rec, r_rec):
    """Max absolute difference over all R keys, and the keys outside TOL."""
    bad = []
    max_diff = 0.0
    for k, b in r_rec.items():
        if k.startswith("_"):
            continue
        if k not in py_rec:
            bad.append(k + " (missing)")
            max_diff = float("inf")
            continue
        a = py_rec[k]
        if a.shape != b.shape:
            bad.append(k + " (length)")
            max_diff = float("inf")
            continue
        both_nan = np.isnan(a) & np.isnan(b)
        d = np.where(both_nan, 0.0, np.abs(a - b))
        if d.size:
            max_diff = max(max_diff, float(np.max(d)))
        if np.any(d > TOL):
            bad.append(k)
    for k in py_rec:
        if not k.startswith("_") and k not in r_rec:
            bad.append(k + " (extra)")
    return len(bad) == 0, max_diff, bad


def report(name, matches, max_diff, r_ms, py_ms, extra=None):
    speedup = r_ms / py_ms if py_ms > 0 else float("inf")
    lines = [
        f"function: {name}",
        f"matches: {str(matches).upper()}",
        f"max_abs_diff: {max_diff:.3g}",
        f"r_ms: {r_ms:.6g}",
        f"translated_ms: {py_ms:.6g}",
        f"speedup: {speedup:.4g}",
    ]
    for k, v in (extra or {}).items():
        lines.append(f"{k}: {v}")
    text = "\n".join(lines) + "\n"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}-summary.txt").write_text(text)
    print(text, end="")
