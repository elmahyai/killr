"""Compare the Python wrapper with R on recycled and infinite inputs."""

import csv
import importlib.util
import statistics
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parents[3]
OUT = ROOT / "packages" / "pbivnorm" / "docs" / "output"

spec = importlib.util.spec_from_file_location(
    "pbivnorm_wrapper", ROOT / "packages" / "pbivnorm" / "pbivnorm" / "pbivnorm.py"
)
wrapper = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(wrapper)

x = np.array([-np.inf, -3, -1, 0, 1, 3, np.inf, -np.inf, 0, np.inf, 2, -2])
y = np.array([np.inf, 0.5, -0.5])
rho = np.array([0, 0.25, -0.75, 0.99])


def read_column(path):
    with path.open(newline="") as handle:
        return np.array([float(row["r_value"]) for row in csv.DictReader(handle)])


def read_times(path):
    with path.open(newline="") as handle:
        return [float(row["seconds"]) for row in csv.DictReader(handle)]


def main():
    r_values = read_column(OUT / "wrapper_r_values.csv")
    r_times = read_times(OUT / "wrapper_r_timings.csv")
    py_values = wrapper.pbivnorm(x, y, rho)  # one untimed call
    times = []
    for _ in range(20):
        t0 = time.perf_counter()
        py_values = wrapper.pbivnorm(x, y, rho)
        times.append(time.perf_counter() - t0)

    both_nan = np.isnan(r_values) & np.isnan(py_values)
    same_nan = np.isnan(r_values) == np.isnan(py_values)
    finite_diff = np.abs(r_values - py_values)
    finite_diff[both_nan] = 0.0
    max_abs_diff = float(np.max(finite_diff))
    matches = bool(np.all(same_nan) and max_abs_diff <= 1e-8)
    r_ms = statistics.median(r_times) * 1000
    py_ms = statistics.median(times) * 1000
    speedup = r_ms / py_ms
    summary = "\n".join(
        [
            f"matches: {'yes' if matches else 'no'}",
            f"max abs diff: {max_abs_diff:.3e}",
            f"R ms: {r_ms:.6f}",
            f"Python ms: {py_ms:.6f}",
            f"speedup: {speedup:.2f}x",
            "",
        ]
    )
    (OUT / "wrapper_proof_summary.txt").write_text(summary)
    print(summary)
    if not matches:
        raise SystemExit("proof failed")


if __name__ == "__main__":
    main()
