"""Proof: mi_inference against R mix::mi.inference (mix 1.0-13).

The inputs are the fixed estimates and standard errors of mi_inference-r.R: five
imputations of four parameters. One call is mi_inference at confidence .95 and then at
.9. The median is over 20 timed calls after one untimed call.
"""

import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mix.mi_inference import mi_inference  # noqa: E402

KEYS = ["est", "std.err", "df", "signif", "lower", "upper", "r", "fminf"]


def num(v):
    arr = np.asarray(v, dtype=float).ravel(order="F")
    return np.where(np.isnan(arr), -999999.0, arr)


est = [np.array([i / 2 + ((i * j * j + 3 * j) % 7 - 3) / 10 for i in range(1, 5)])
       for j in range(1, 6)]
std = [np.array([0.2 + ((i + 2 * j) % 5) / 20 for i in range(1, 5)])
       for j in range(1, 6)]


def one():
    a = mi_inference(est, std, confidence=.95)
    b = mi_inference(est, std, confidence=.9)
    return np.concatenate([num(a[k]) for k in KEYS] + [num(b[k]) for k in KEYS])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for v in value:
    print("%.17g" % v)
print("%.17g" % statistics.median(elapsed))
