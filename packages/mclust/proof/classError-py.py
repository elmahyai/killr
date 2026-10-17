import importlib.util
import statistics
import sys
import time
from pathlib import Path

import numpy as np

_module_path = Path(__file__).resolve().parent.parent / "mclust" / "class_error.py"
_spec = importlib.util.spec_from_file_location("class_error", _module_path)
assert _spec and _spec.loader
_class_error = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_class_error)
classError = _class_error.classError


class Factor:
    """Minimal R factor stand-in (levels + integer codes)."""

    def __init__(self, codes, levels):
        self.codes = list(codes)
        self.levels = [str(level) for level in levels]

    def labels(self):
        return [self.levels[code - 1] for code in self.codes]


def flatten(out):
    vals = [out["errorRate"]]
    vals.extend(out["misclassified"])
    return vals


def one():
    a = np.tile(np.arange(1, 4), 3)
    b = np.tile(np.array(["A", "B", "C"]), 3)
    v1 = flatten(classError(a, b))
    a2 = np.array([1, 1, 1, 1, 2, 2, 2, 1, 3], dtype=int)
    b2 = np.array(["C", "A", "A", "B", "B", "B", "C", "C", "A"])
    v2 = flatten(classError(a2, b2))
    class_arr = Factor([5, 5, 5, 2, 5, 3, 1, 2, 1, 1], [1, 2, 3, 4, 5])
    pred = np.array([3, 5, 5, 2, 3, 3, 1, 5, 1, 1], dtype=int)
    v3 = flatten(classError(pred, class_arr))
    return v1 + v2 + v3


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
