"""Fixed-value and timing proof for the requested locfit helper exports."""

from __future__ import annotations

import statistics
import time
from pathlib import Path
import subprocess

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).parents[1] / "locfit"))
sys.path.insert(0, str(Path(__file__).parents[1]))
from km_mrl import km_mrl
from lflim import lflim
from lfgrid import lfgrid
from sjpi import sjpi
from spence_15 import spence_15
from spence_21 import spence_21

OUT = Path(__file__).parents[1] / "docs" / "output"
TOL = 1e-8


def timed(fn):
    fn()
    values = []
    for _ in range(20):
        start = time.perf_counter()
        for _ in range(20):
            fn()
        values.append((time.perf_counter() - start) * 1000 / 20)
    return statistics.median(values)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    subprocess.run(["Rscript", "--vanilla", "packages/locfit/proof/requested_proof.R"],
                   cwd=Path(__file__).parents[3], check=True)
    cases = {
        "km.mrl": (lambda: km_mrl([3, 1, 2, 4], [0, 1, 1, 0]),
                   "locfit_r_km_mrl.txt"),
        "lfgrid": (lambda: lfgrid(2)["mg"], np.repeat(2, 10)),
        "lflim": (lambda: lflim({"a": [2, 4]}, ["a"], [0, 0]),
                   "locfit_r_lflim.txt"),
        "sjpi": (lambda: sjpi(np.linspace(-1, 1, 20), [.5, .8]),
                 "locfit_r_sjpi.txt"),
        "spence.15": (lambda: spence_15(np.arange(1, 21)),
                      "locfit_r_spence_15.txt"),
        "spence.21": (lambda: spence_21(np.arange(1, 21)),
                      "locfit_r_spence_21.txt"),
    }
    cases["lfgrid"] = (lambda: lfgrid(2)["mg"], "locfit_r_lfgrid.txt")
    lines = ["tolerance,1e-8"]
    r_times = {}
    for line in (OUT / "locfit_requested_r_timing.txt").read_text().splitlines():
        name, value = line.split(",r_ms=")
        r_times[name] = float(value)
    for name, (call, reference) in cases.items():
        reference = np.loadtxt(OUT / reference)
        value = np.asarray(call(), dtype=float)
        diff = float(np.max(np.abs(value - reference)))
        ms = timed(call)
        lines.append(f"{name},matches={diff <= TOL},max_abs_diff={diff:.17g},"
                     f"r_ms={r_times[name]:.17g},translated_ms={ms:.17g},"
                     f"speedup={r_times[name] / ms:.17g}")
        np.savetxt(OUT / f"locfit_python_{name.replace('.', '_')}.txt",
                   value.reshape(-1), fmt="%.17g")
    (OUT / "locfit_requested_compare.txt").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
