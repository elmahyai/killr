"""Bit-exact proof of nlme_mixedem.mixed_em against R's mixed_EM.

Runs ``mixedem-r.R`` (six lme fits, the first ``mixed_EM`` input of each),
then replays the same inputs through ``nlme_mixedem.mixed_em``. The R
outputs are the reference: ``precvec`` (the EM factor), ``logLik``, ``Ra``
and ``lRSS``. Each quantity's largest absolute difference is reported, and
the case matches when every difference is exactly zero.

Timing: one untimed call, then the median of 20 timed calls, per case.
Speedup = R median / Python median.

Outputs: ``docs/output/mixedem-r.txt``, ``docs/output/mixedem-python.txt``,
``docs/output/mixedem-compare.json``.
"""

from __future__ import annotations

import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

import nlme_mixedem

PACKAGE = Path(__file__).resolve().parents[1]
PROOF = PACKAGE / "proof"
OUTPUT = PACKAGE / "docs" / "output"
REPEATS = 20


def run_r() -> str:
    done = subprocess.run(
        ["Rscript", str(PROOF / "mixedem-r.R")], check=True, capture_output=True, text=True
    )
    return done.stdout


def replay(case: dict) -> tuple[list[float], float, list[float], float]:
    updated, log_lik, ra, lrss = nlme_mixedem.mixed_em(
        case["Xy"],
        case["dims"],
        list(case["precvec"]),
        int(case["niter"]),
        case["pdCl"],
        int(case["RML"]),
        float(case["sigma"][0]),
    )
    return list(updated), float(log_lik), list(ra), float(lrss)


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    r_text = run_r()
    (OUTPUT / "mixedem-r.txt").write_text(r_text)
    r_cases = json.loads(r_text.strip().splitlines()[-1])["cases"]

    py_lines = []
    summary = {}
    for case in r_cases:
        name = case["name"]
        out = case["out"]
        precvec, log_lik, ra, lrss = replay(case)
        diffs = {
            "precvec": max(abs(a - b) for a, b in zip(precvec, out["precvec"])),
            "logLik": abs(log_lik - out["logLik"][0]),
            "Ra": max(abs(a - b) for a, b in zip(ra, out["Ra"])),
            "lRSS": abs(lrss - out["lRSS"][0]),
        }
        timings = []
        replay(case)
        for _ in range(REPEATS):
            started = time.perf_counter()
            replay(case)
            timings.append((time.perf_counter() - started) * 1000)
        py_ms = statistics.median(timings)
        r_ms = case["median_ms"]
        matches = all(value == 0.0 for value in diffs.values())
        summary[name] = {
            "matches_bit_exact": bool(matches),
            "max_abs_diff_by_quantity": diffs,
            "max_abs_diff": max(diffs.values()),
            "r_ms": r_ms,
            "python_ms": py_ms,
            "speedup": r_ms / py_ms,
        }
        py_lines.append(
            json.dumps({"name": name, "precvec": precvec, "logLik": [log_lik], "Ra": ra, "lRSS": [lrss], "median_ms": py_ms})
        )

    (OUTPUT / "mixedem-python.txt").write_text("\n".join(py_lines) + "\n")
    (OUTPUT / "mixedem-compare.json").write_text(json.dumps(summary, indent=2) + "\n")
    for name, row in summary.items():
        print(
            f"{name}: bit_exact={row['matches_bit_exact']} max_abs_diff={row['max_abs_diff']:.3e} "
            f"r_ms={row['r_ms']:.3f} python_ms={row['python_ms']:.3f} speedup={row['speedup']:.2f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
