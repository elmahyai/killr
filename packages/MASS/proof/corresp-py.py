import statistics
import time

import numpy as np

from mass.corresp import corresp


def one():
    x = np.array(
        [12, 5, 7, 3, 8, 15, 4, 9, 6, 11, 2, 10],
        dtype=float,
    ).reshape(4, 3, order="F")
    ct = corresp(x, nf=2)
    return np.concatenate(
        [
            np.asarray(ct["cor"], dtype=float).reshape(-1),
            np.asarray(ct["rscore"], dtype=float).reshape(-1, order="F"),
            np.asarray(ct["cscore"], dtype=float).reshape(-1, order="F"),
            np.asarray(ct["Freq"], dtype=float).reshape(-1, order="F"),
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
flat = np.asarray(value, dtype=float).reshape(-1)
print("\n".join("%.17g" % item for item in flat))
print("%.17g" % statistics.median(elapsed))
