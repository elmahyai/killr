"""Compare the R and Python plot proofs and write one comparison per function.

Each proof writes <fn>-r.txt and <fn>-py.txt: a CASE line per case, then the
records the function logged (``TAG n v1 ... `` with each field as its length
and its values; see plot_record.R and plot_log.py). Times are in
<fn>-r-time.txt and <fn>-py-time.txt, the median of 20 timed calls in
milliseconds.

A function matches when every case has the same CASE names, the same record
tags and token counts, the same strings, and every number differs by at most
1e-8. Speedup is R time over Python time on the data computation.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

TOLERANCE = 1e-8
PROOF = Path(__file__).resolve().parent
OUTPUT = PROOF.parent / "docs" / "output"
FUNCTIONS = [
    "errorBars", "mclust1Dplot", "mclust2Dplot", "mvn2plot", "surfacePlot",
    "uncerPlot", "clPairs", "clPairsLegend", "coordProj", "randProj",
]


def read_lines(path: Path) -> list[str]:
    return [line.rstrip("\n") for line in path.read_text().splitlines() if line.strip() != ""]


def as_float(token: str) -> float | None:
    try:
        return float(token)
    except ValueError:
        return None


def compare(r_lines: list[str], py_lines: list[str]) -> tuple[bool, float, int, str]:
    """Return (matches, max_abs_diff, numbers compared, first mismatch or '')."""
    if len(r_lines) != len(py_lines):
        return False, math.inf, 0, f"line count R={len(r_lines)} Python={len(py_lines)}"
    max_diff = 0.0
    numbers = 0
    for idx, (rl, pl) in enumerate(zip(r_lines, py_lines)):
        rt, pt = rl.split(), pl.split()
        if len(rt) != len(pt):
            return False, math.inf, numbers, f"line {idx}: token count {len(rt)} vs {len(pt)}"
        if rt[0] != pt[0]:
            return False, math.inf, numbers, f"line {idx}: tag {rt[0]} vs {pt[0]}"
        for a, b in zip(rt[1:], pt[1:]):
            fa, fb = as_float(a), as_float(b)
            if fa is None or fb is None:
                if a != b:
                    return False, math.inf, numbers, f"line {idx} ({rt[0]}): '{a}' vs '{b}'"
                continue
            numbers += 1
            max_diff = max(max_diff, abs(fa - fb))
    matches = max_diff <= TOLERANCE
    detail = "" if matches else f"largest difference {max_diff:.3e} exceeds {TOLERANCE:g}"
    return matches, max_diff, numbers, detail


def split_cases(lines: list[str]) -> dict[str, list[str]]:
    cases: dict[str, list[str]] = {}
    current = None
    for line in lines:
        if line.startswith("CASE "):
            current = line[5:]
            cases[current] = []
        elif current is not None:
            cases[current].append(line)
    return cases


def main(names: list[str]) -> int:
    failed = False
    for name in names:
        r_text = read_lines(OUTPUT / f"{name}-r.txt")
        py_text = read_lines(OUTPUT / f"{name}-py.txt")
        r_ms = float((OUTPUT / f"{name}-r-time.txt").read_text().split()[0])
        py_ms = float((OUTPUT / f"{name}-py-time.txt").read_text().split()[0])
        r_cases = split_cases(r_text)
        py_cases = split_cases(py_text)
        notes: list[str] = []
        matches = list(r_cases) == list(py_cases)
        if not matches:
            notes.append(f"case names R={list(r_cases)} Python={list(py_cases)}")
        max_abs = 0.0
        numbers = 0
        records = 0
        for case in r_cases:
            if case not in py_cases:
                matches = False
                continue
            ok, diff, count, detail = compare(r_cases[case], py_cases[case])
            records += len(r_cases[case])
            numbers += count
            max_abs = max(max_abs, diff)
            if not ok:
                matches = False
                notes.append(f"{case}: {detail}")
        if max_abs > TOLERANCE:
            matches = False
        speedup = r_ms / py_ms if py_ms > 0 else math.inf
        failed = failed or not matches
        line = (
            f"{name} matches={'yes' if matches else 'no'} cases={len(r_cases)} "
            f"records={records} numbers={numbers} max_abs_diff={max_abs:.3e} "
            f"r_ms={r_ms:.6g} python_ms={py_ms:.6g} speedup={speedup:.4g}"
        )
        text = [line] + [f"  note: {n}" for n in notes]
        print("\n".join(text))
        (OUTPUT / f"{name}-compare.txt").write_text("\n".join(text) + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or FUNCTIONS))
