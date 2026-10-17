import statistics
import time

import numpy as np

from mass.qda import qda, qda_values


def one():
    train = np.array(
        [
            [1.2, 0.5],
            [1.5, 0.7],
            [1.1, 0.9],
            [1.8, 0.4],
            [1.3, 0.6],
            [3.1, 2.2],
            [3.4, 2.5],
            [2.9, 2.1],
            [3.6, 2.8],
            [3.2, 2.4],
            [5.5, 4.1],
            [5.8, 4.3],
            [5.2, 3.9],
            [6.1, 4.5],
            [5.6, 4.0],
        ],
        dtype=float,
    )
    cl = np.array(["A"] * 5 + ["B"] * 5 + ["C"] * 5)
    z = qda(train, cl)
    return qda_values(z)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
