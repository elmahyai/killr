"""Proof, Python side: lmom_kernel (Rust, via PyO3) against R lmom 3.3.

Runs every case in cases.csv on the fixed samples in fixed_samples.csv,
compares with docs/output/r_values.csv (written by r_proof.R), and writes
docs/output/lmom_proof.txt. Timing: one untimed call, then the median of
20 calls with time.perf_counter().

Run R first:   Rscript packages/lmom/proof/r_proof.R
Then:          .venv/bin/python packages/lmom/proof/python_proof.py
"""

from __future__ import annotations

import csv
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

import lmom_kernel as K

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "docs" / "output"
TOL = 1e-8
REPS = 20


def load_samples() -> dict[str, np.ndarray]:
    groups: dict[str, list[float]] = defaultdict(list)
    with (HERE / "fixed_samples.csv").open(newline="") as handle:
        for row in csv.DictReader(handle):
            groups[row["sample"]].append(float(row["x"]))
    return {name: np.asarray(values, dtype=np.float64) for name, values in groups.items()}


def load_cases() -> list[dict[str, str]]:
    with (HERE / "cases.csv").open(newline="") as handle:
        return list(csv.DictReader(handle))


def parse_numbers(text: str) -> np.ndarray:
    return np.asarray([float(v) for v in text.split()], dtype=np.float64)


def run_case(routine: str, args: str, nmom: int, samples: dict[str, np.ndarray]):
    """Return (values, ifail) for one case, using the Rust kernel."""
    if routine in ("samlm", "samlm_ratio"):
        x = samples[args]
        values = K.samlm(x, nmom, True, routine == "samlm_ratio")
        return np.asarray(values), 0
    if routine.startswith("lmr_"):
        values, ifail = getattr(K, routine)(parse_numbers(args), nmom)
        return np.asarray(values), int(ifail)
    if routine.startswith("pel_"):
        values, ifail = getattr(K, routine)(parse_numbers(args))
        return np.asarray(values), int(ifail)
    raise ValueError(f"unknown routine {routine}")


def median_seconds(fn) -> float:
    fn()  # one untimed call
    times = []
    for _ in range(REPS):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return statistics.median(times)


def load_r_values() -> dict[str, tuple[np.ndarray, int]]:
    collected: dict[str, list[tuple[int, float]]] = defaultdict(list)
    ifails: dict[str, int] = {}
    with (OUT / "r_values.csv").open(newline="") as handle:
        for row in csv.DictReader(handle):
            collected[row["id"]].append((int(row["index"]), float(row["value"])))
            ifails[row["id"]] = int(row["ifail"])
    out = {}
    for case_id, pairs in collected.items():
        pairs.sort()
        out[case_id] = (np.asarray([v for _, v in pairs]), ifails[case_id])
    return out


def load_r_timings() -> dict[str, float]:
    with (OUT / "r_timings.csv").open(newline="") as handle:
        return {row["id"]: float(row["r_median_seconds"]) for row in csv.DictReader(handle)}


def main() -> int:
    samples = load_samples()
    cases = load_cases()
    r_values = load_r_values()
    r_times = load_r_timings()

    lines = []
    lines.append("lmom proof: Rust lmom_kernel vs R lmom 3.3")
    lines.append(f"tolerance: max abs diff <= {TOL:g}; timing: median of {REPS} calls after 1 untimed call")
    lines.append("")
    header = f"{'case':<22}{'routine':<14}{'n':>3}{'max_abs_diff':>16}{'ifail R/Rust':>14}{'R_s':>12}{'Rust_s':>12}{'speedup':>10}"
    lines.append(header)
    lines.append("-" * len(header))

    overall_max = 0.0
    failures = []
    for case in cases:
        case_id = case["id"]
        routine = case["routine"]
        nmom = int(case["nmom"])
        rust_values, rust_ifail = run_case(routine, case["args"], nmom, samples)
        r_vals, r_ifail = r_values[case_id]
        if rust_values.shape != r_vals.shape:
            failures.append(f"{case_id}: shape {rust_values.shape} vs {r_vals.shape}")
            continue
        diff = float(np.max(np.abs(rust_values - r_vals)))
        overall_max = max(overall_max, diff)
        if diff > TOL or rust_ifail != r_ifail:
            failures.append(f"{case_id}: max diff {diff:.3e}, ifail {rust_ifail} vs {r_ifail}")

        rust_s = median_seconds(lambda: run_case(routine, case["args"], nmom, samples))
        r_s = r_times[case_id]
        speedup = r_s / rust_s if rust_s > 0 else float("inf")
        lines.append(
            f"{case_id:<22}{routine:<14}{nmom:>3}{diff:>16.3e}"
            f"{f'{r_ifail}/{rust_ifail}':>14}{r_s:>12.3e}{rust_s:>12.3e}{speedup:>10.1f}"
        )

    lines.append("")
    lines.append(f"cases: {len(cases)}")
    lines.append(f"overall max abs diff: {overall_max:.3e}")
    lines.append("result: PASS" if not failures else "result: FAIL")
    for item in failures:
        lines.append(f"  {item}")
    text = "\n".join(lines) + "\n"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "lmom_proof.txt").write_text(text)
    print(text)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
