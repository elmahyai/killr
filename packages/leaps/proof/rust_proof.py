"""Proof, Python side: the Rust leaps kernel (crate crates/leaps) on design.csv.

Run from packages/leaps/proof (see run_proof.sh). Writes:
  ../docs/output/rust_subsets.csv  selected subsets and their RSS values
  ../docs/output/rust_timings.txt  one untimed call, then 20 timed calls

The R wrapper bookkeeping for the intercept is done here: a column of ones is
prepended, the first searchable position is 2, and nvmax is min(nvmax, p) + 1.
"""

import statistics
import importlib.util
import sys
import time
import types
from pathlib import Path

import numpy as np

import leaps as kernel

# Load source wrappers under a private package name so the installed
# ``leaps.leaps`` extension and Python ``leaps.py`` do not collide.
SOURCE = Path(__file__).resolve().parents[1] / "leaps"
pkg = types.ModuleType("_leaps_wrapper")
pkg.__path__ = [str(SOURCE)]
sys.modules[pkg.__name__] = pkg
def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        f"{pkg.__name__}.{name}", SOURCE / f"{name}.py",
        submodule_search_locations=None,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
wrapper = _load("leaps")
regsubsets = _load("regsubsets").regsubsets
low_level_leaps = wrapper.leaps

NVMAX = 10
NBEST = 5
N_TIMED = 20

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "docs" / "output"


def load_design() -> tuple[np.ndarray, np.ndarray]:
    data = np.loadtxt(HERE / "design.csv", delimiter=",", skiprows=1)
    y = np.ascontiguousarray(data[:, 0])
    x = np.ascontiguousarray(data[:, 1:])
    return x, y


def run_search(x: np.ndarray, y: np.ndarray):
    fit = regsubsets(x, y, nbest=NBEST, nvmax=NVMAX, method="exhaustive")
    low = low_level_leaps(x, y, nbest=NBEST, nvmax=NVMAX, method="exhaustive")
    np.testing.assert_allclose(fit.search.ress, low.ress, rtol=0.0, atol=0.0)
    return fit


def subset_rows(ress: np.ndarray, lopt: np.ndarray, nvmax_eff: int):
    rows = []
    for i in range(1, nvmax_eff + 1):
        lo = i * (i - 1) // 2
        hi = lo + i
        for j in range(1, NBEST + 1):
            rss = float(ress[i - 1, j - 1])
            if rss >= 1e35:
                continue
            vars_ = sorted(int(v) for v in lopt[lo:hi, j - 1])
            rows.append((i - 1, j, rss, vars_))
    return rows


def main() -> None:
    x, y = load_design()
    n, p = x.shape

    # One untimed call.
    fit = run_search(x, y)

    # Median of 20 timed calls, using time.perf_counter().
    times = []
    for _ in range(N_TIMED):
        t0 = time.perf_counter()
        fit = run_search(x, y)
        times.append(time.perf_counter() - t0)

    nvmax_eff = min(NVMAX, p) + 1
    rows = subset_rows(fit.search.ress, fit.search.lopt, nvmax_eff)

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "rust_subsets.csv").open("w") as fh:
        fh.write("predictors,rank,rss,vars\n")
        for predictors, rank, rss, vars_ in rows:
            fh.write(
                f"{predictors},{rank},{rss:.17g},{';'.join(str(v) for v in vars_)}\n"
            )

    median_s = statistics.median(times)
    lines = [
        f"Python {__import__('sys').version.split()[0]}, leaps kernel (crates/leaps)",
        f"regsubsets(method='exhaustive') n={n} p={p} nvmax={NVMAX} nbest={NBEST}",
        f"untimed calls: 1, timed calls: {N_TIMED} (time.perf_counter)",
        "timed seconds: " + " ".join(f"{t:.6f}" for t in times),
        f"median_seconds: {median_s:.9f}",
        f"subsets_recorded: {len(rows)}",
    ]
    (OUT / "rust_timings.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
