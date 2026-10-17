"""Proof: locfit.plotting.lcvplot against R's lcvplot (locfit 1.5-9.12).

The translated function is packages/locfit/locfit/plotting.py, with its helper
packages/locfit/locfit/lcv.py. Both are loaded here as the subpackage
``locfit_sub``. The top-level packages/locfit/plotting.py and lcv.py are older
copies and are not the port, so they are not imported (see the note in
experience/locfit-duplicate-plot-modules.md).

R reference: lcvplot-r.R (through _plot-r-common.R), written to
packages/locfit/docs/output/lcvplot/r_values.txt and r_ms.txt.

Each value (df = infl, values = cv, one row per bandwidth) is compared with R
within 1e-8. Timing: one untimed call, then the median of 20 timed calls with
time.perf_counter(). speedup = R time / Python time.

Run from the repository root:
    .venv/bin/python packages/locfit/proof/lcvplot-py.py
"""

from __future__ import annotations

import pathlib
import statistics
import sys
import time
import types

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _locfit10 as L  # noqa: E402

TOL = 1e-8
NAME = "lcvplot"
OUT = L.PKG / "docs" / "output" / NAME

L.load_translated()
import locfit_translated.locfit_raw as _locfit_raw_mod  # noqa: E402

# locfit/plotting.py and locfit/lcv.py import the bare name locfit_raw when they
# are loaded outside the package; alias it to the crate-backed wrapper.
sys.modules.setdefault("locfit_raw", _locfit_raw_mod)

# Load the locfit/ subpackage (the port) as a package of its own. Its files use
# relative imports (.criteria, .lcv), so a package object with the right
# __path__ is enough. The top-level plotting.py is not used.
_sub = types.ModuleType("locfit_sub")
_sub.__path__ = [str(L.PKG / "locfit")]
sys.modules["locfit_sub"] = _sub
import locfit_sub.plotting as plotting  # noqa: E402

x = np.linspace(0, 1, 12)
y = np.sin(2 * x) + 0.1 * np.cos(5 * x)
alpha = np.array([[0.4], [0.6], [0.8]])


def call():
    return plotting.lcvplot(alpha, x=x, y=y, deg=1, kern="tcub")


def time_median_ms(fn):
    """One untimed call, then the median of 20 timed calls (perf_counter), in ms."""
    fn()
    samples = []
    for _ in range(20):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000.0)
    return statistics.median(samples)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    z = call()
    got = np.c_[z["df"], z["values"]]
    np.savetxt(OUT / "py_values.txt", got, delimiter=",")
    want = np.loadtxt(OUT / "r_values.txt", delimiter=",", ndmin=2)
    max_diff = float(np.max(np.abs(got - want)))
    matches = max_diff <= TOL

    r_ms = float((OUT / "r_ms.txt").read_text())
    py_ms = time_median_ms(call)

    fig, ax = plt.subplots()
    ax.plot(z["df"], z["values"], marker="o")
    ax.set(xlabel="Fitted DF", ylabel=z["cri"])
    fig.savefig(OUT / "py.svg")
    plt.close(fig)

    print(
        f"{NAME},matches={'true' if matches else 'false'},max_abs_diff={max_diff:.6g},"
        f"r_ms={r_ms:.6g},translated_ms={py_ms:.6g},speedup={r_ms / py_ms:.6g},"
        f"python=locfit.plotting.lcvplot"
    )
    sys.exit(0 if matches else 1)


if __name__ == "__main__":
    main()
