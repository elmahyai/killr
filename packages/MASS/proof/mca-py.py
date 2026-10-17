import importlib.util
import statistics
import sys
import time
import types

import numpy as np

_PKG = "/home/ahmed/killr_projects/killr/packages/MASS/mass"


def _load_module(qualified: str, path: str):
    spec = importlib.util.spec_from_file_location(qualified, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[qualified] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


if "mass" not in sys.modules:
    sys.modules["mass"] = types.ModuleType("mass")
_load_module("mass.errors", f"{_PKG}/errors.py")
_mca = _load_module("mass.mca", f"{_PKG}/mca.py")
mca = _mca.mca


class _Factor:
    __slots__ = ("values", "attributes", "storage")

    def __init__(self, values, levels, names=None):
        self.storage = "integer"
        self.values = list(values)
        attrs = {"class": "factor", "levels": list(levels)}
        if names is not None:
            attrs["names"] = list(names)
        self.attributes = attrs


def one():
    df = {
        "x": _Factor([1, 2, 1, 3, 2, 3], ["a", "b", "c"], names=["r1", "r2", "r3", "r4", "r5", "r6"]),
        "y": _Factor([1, 2, 2, 1, 1, 2], ["L", "M"], names=["r1", "r2", "r3", "r4", "r5", "r6"]),
        "z": _Factor([1, 2, 1, 1, 2, 2], ["p", "q"], names=["r1", "r2", "r3", "r4", "r5", "r6"]),
    }
    fit = mca(df, nf=2, abbrev=False)
    return np.concatenate(
        [
            np.asarray(fit.rs, dtype=float).reshape(-1, order="F"),
            np.asarray(fit.cs, dtype=float).reshape(-1, order="F"),
            np.asarray(fit.fs, dtype=float).reshape(-1, order="F"),
            np.asarray(fit.d, dtype=float).reshape(-1),
            np.array([fit.p], dtype=float),
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
