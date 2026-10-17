import contextlib
import importlib.util
import io
import statistics
import time
from pathlib import Path

import numpy as np

_MODULE = Path(__file__).resolve().parents[1] / "mass" / "negexp_ssival.py"
_SPEC = importlib.util.spec_from_file_location("negexp_ssival", _MODULE)
assert _SPEC is not None and _SPEC.loader is not None
negexp_ssival = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(negexp_ssival)
negexp_ssival = negexp_ssival.negexp_ssival

X = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=float)
Y = np.array([2.1, 3.2, 3.9, 3.1, 2.0], dtype=float)
M_CALL = {
    "b0": "b0",
    "b1": "b1",
    "th": "th",
    "x": "x",
}
DATA = {"x": X, "y": Y}


def one():
    with contextlib.redirect_stdout(io.StringIO()):
        res = negexp_ssival(M_CALL, DATA, "y")
    return np.array([res["b0"], res["b1"], res["th"]], dtype=float)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
flat = np.asarray(value, dtype=float).reshape(-1)
print("\n".join("%.17g" % item for item in flat))
print("%.17g" % statistics.median(elapsed))
