import statistics
import sys
import time
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
# Load the nlme modules without running nlme/__init__.py, which imports the
# onecomp extension (phenoModel) that is not built in this environment.
if "nlme" not in sys.modules:
    _pkg = types.ModuleType("nlme")
    _pkg.__path__ = [str(ROOT / "nlme")]
    sys.modules["nlme"] = _pkg

from nlme.lmecontrol import lmeControl  # noqa: E402

FIELDS = [
    "maxIter", "msMaxIter", "tolerance", "niterEM", "msMaxEval",
    "msTol", "msVerbose", "returnObject", "gradHess", "apVar",
    ".relStep", "minAbsParApVar", "natural", "sigma", "allow.n.lt.q",
]


def one():
    a = lmeControl()
    b = lmeControl(
        maxIter=30, msMaxIter=20, tolerance=1e-4,
        niterEM=10, msMaxEval=100, msTol=1e-5,
        msVerbose=True, returnObject=True, gradHess=False,
        apVar=False, minAbsParApVar=0.1, opt="optim",
        optimMethod="Nelder-Mead", natural=False,
        sigma=0.5, allow_n_lt_q=True,
    )
    values = []
    for control in (a, b):
        values.extend(float(control[name]) for name in FIELDS)
    values += [
        float(a["opt"] == "nlminb"),
        float(b["opt"] == "optim"),
        float(a["optimMethod"] == "BFGS"),
        float(b["optimMethod"] == "Nelder-Mead"),
        float(len(a)),
        float(len(b)),
    ]
    return np.asarray(values, dtype=np.float64)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (",".join("%.17g" % float(part) for part in value), statistics.median(elapsed))
)
