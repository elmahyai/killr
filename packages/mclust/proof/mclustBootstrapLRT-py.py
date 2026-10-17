"""Proof: Python mclustBootstrapLRT on the same inputs and seed as mclustBootstrapLRT-r.R.

Prints the same values as the R proof (one per line, %.17g) and the median of 20 timed
calls of the default call (ms) as the last line. Run with the project venv, because
the translated em/estep/mvnXXX path imports the mclust_kernels extension.
"""

import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "boot"))

from boot.rng import set_seed  # noqa: E402
from mclust._sim_core import r_rnorm  # noqa: E402
from mclust.mclust_bootstrap_lrt import mclust_bootstrap_lrt  # noqa: E402


def make_data():
    set_seed(42)
    a = r_rnorm(15, 0, 1)
    b = r_rnorm(15, 0, 1)
    c = r_rnorm(15, 3, 1)
    d = r_rnorm(15, 3, 1)
    return np.vstack([np.column_stack([a, b]), np.column_stack([c, d])])


def record(out):
    return (
        [float(g) for g in out["G"]]
        + [float(v) for v in out["obs"]]
        + [float(v) for v in out["p.value"]]
        + [float(v) for v in np.asarray(out["boot"], dtype=float).ravel(order="F")]
    )


def one():
    # The default call: only modelName is given; nboot = 999, level = 0.05, maxG = NULL.
    return record(mclust_bootstrap_lrt(make_data(), model_name="EEE"))


def small():
    return record(mclust_bootstrap_lrt(make_data(), model_name="EEE",
                                       nboot=15, max_g=2, verbose=False))


default_part = one()
value = [float(len(default_part))] + default_part + small()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
