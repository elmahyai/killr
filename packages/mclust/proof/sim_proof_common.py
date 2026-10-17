"""Record reader, comparator, and timer for the sim proofs (mclust 6.1.3).

The R side (sim_proof_common.R) writes docs/output/<name>-r.txt and
proof/<name>-r-ms.txt. This side runs the same cases, compares every number
within 1e-8 (NA matches NA; dims and column names must be equal), times the
first case as the median of 20 calls after one untimed pass, and writes
docs/output/<name>-py.txt.
"""

from __future__ import annotations

import math
import statistics
import sys
import time
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "output"
PROOF = ROOT / "proof"
TOL = 1e-8


def _fmt(x) -> str:
    x = float(x)
    if math.isnan(x):
        return "NA"
    return "%.17g" % x


def record_lines(case_id: str, m) -> list[str]:
    if m is None:
        return [f"case\t{case_id}", "null\t1"]
    a = np.asarray(m, dtype=float)
    cn = getattr(m, "colnames", None)
    out = [
        f"case\t{case_id}",
        f"dim\t{a.shape[0]}\t{a.shape[1]}",
        "colnames\t" + ("NULL" if cn is None else ",".join(cn)),
    ]
    for row in a:
        out.append("\t".join(["row"] + [_fmt(v) for v in row]))
    return out


def _num(tok: str):
    try:
        return float(tok)
    except ValueError:
        return None


def compare(ref: list[str], got: list[str]) -> tuple[bool, float]:
    """(matches, max_abs_diff). Numbers within TOL; NA matches NA; other tokens exact."""
    if len(ref) != len(got):
        return False, math.inf
    ok = True
    max_diff = 0.0
    for a, b in zip(ref, got):
        ta, tb = a.split("\t"), b.split("\t")
        if len(ta) != len(tb) or ta[0] != tb[0]:
            return False, math.inf
        for x, y in zip(ta[1:], tb[1:]):
            if x == "NA" or y == "NA":
                if x != y:
                    ok = False
                    max_diff = math.inf
                continue
            fx, fy = _num(x), _num(y)
            if fx is None or fy is None:
                if x != y:
                    ok = False
                continue
            max_diff = max(max_diff, abs(fx - fy))
    if max_diff > TOL:
        ok = False
    return ok, max_diff


def timed_median_ms(fn, reps: int = 20) -> float:
    """Median of ``reps`` timed calls in milliseconds (time.perf_counter)."""
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000.0)
    return statistics.median(times)


def split_cases(lines: list[str]) -> dict[str, list[str]]:
    """Split a record into {case_id: its lines}, in order."""
    blocks: dict[str, list[str]] = {}
    cur = None
    for line in lines:
        if line.startswith("case\t"):
            cur = line.split("\t", 1)[1]
            blocks[cur] = []
        if cur is not None:
            blocks[cur].append(line)
    return blocks


def per_case_lines(ref: list[str], got: list[str]) -> list[str]:
    """One summary line per case: its match and max abs diff against R."""
    ref_b, got_b = split_cases(ref), split_cases(got)
    out = []
    for cid, rl in ref_b.items():
        gl = got_b.get(cid, [])
        ok, d = compare(rl, gl)
        out.append(f"# case\t{cid}\t{'yes' if ok else 'no'}\t{d:.3g}")
    return out


def run_sim_proof(name: str, cases, timed=None, per_case: bool = False) -> None:
    """``cases``: list of (case_id, callable). ``timed`` (optional) is called once per repetition;
    by default the first case is timed. ``per_case`` adds one match line per case."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        results = [fn() for _, fn in cases]  # one untimed pass
        lines: list[str] = []
        for (cid, _), m in zip(cases, results):
            lines += record_lines(cid, m)
        py_ms = timed_median_ms(timed if timed is not None else cases[0][1])
    ref = (OUT / f"{name}-r.txt").read_text().splitlines()
    matches, max_diff = compare(ref, lines)
    r_ms = float((PROOF / f"{name}-r-ms.txt").read_text())
    speedup = r_ms / py_ms if py_ms > 0 else math.nan
    summary = [
        f"# {name}",
        f"# matches\t{'yes' if matches else 'no'}",
        f"# max_abs_diff\t{max_diff:.3g}",
        f"# R_ms\t{r_ms:.6g}",
        f"# Python_ms\t{py_ms:.6g}",
        f"# speedup\t{speedup:.4g}",
    ]
    if per_case:
        summary += per_case_lines(ref, lines)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}-py.txt").write_text("\n".join(summary + lines) + "\n")
    print("\n".join(summary))
    sys.stdout.flush()
