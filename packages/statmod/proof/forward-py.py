import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.forward import forward


def one():
    y12 = np.array(
        [
            -0.292346,
            1.28909,
            -0.414994,
            -0.441552,
            0.542544,
            -0.279449,
            0.214359,
            0.310769,
            -0.0893034,
            0.437588,
            0.325777,
            -0.39283,
        ],
        dtype=float,
    )
    x12 = np.array(
        [
            1.181,
            -0.685,
            0.737,
            -0.962,
            0.276,
            -0.419,
            0.508,
            -0.138,
            0.461,
            0.882,
            0.313,
            -0.164,
            0.591,
            -0.733,
            0.219,
            -0.446,
            0.293,
            -0.375,
            0.428,
            -0.227,
            0.162,
            -1.12,
            0.229,
            -0.502,
            0.576,
            -0.542,
            0.334,
            -0.594,
            -0.102,
            0.359,
            0.577,
            -0.617,
            0.198,
            -0.481,
            0.421,
            0.685,
            0.497,
            0.368,
            -0.212,
            -0.371,
            0.156,
            -0.268,
            -0.219,
            -0.556,
            -0.062,
            -0.908,
            0.655,
            -0.673,
            0.637,
            0.115,
            -0.229,
            0.702,
            0.117,
            -0.489,
            0.409,
            -0.155,
            -0.235,
            0.447,
            0.332,
            0.813,
            0.224,
            -0.298,
            0.349,
            0.878,
            0.553,
            -0.428,
            -0.304,
            -0.318,
            0.517,
            -0.476,
            -0.267,
            -0.596,
            0.286,
            0.611,
            0.502,
            -0.362,
            0.283,
            -1.026,
            -0.828,
            -0.789,
            0.389,
            -0.147,
            0.244,
            -0.521,
        ],
        dtype=float,
    ).reshape(12, 7, order="F")
    xk12 = np.array(
        [
            0.314,
            -0.218,
            0.618,
            -0.412,
            0.205,
            -0.731,
            0.489,
            -0.166,
            0.352,
            -0.604,
            0.278,
            -0.395,
            -0.527,
            0.643,
            -0.357,
            0.471,
            -0.589,
            0.326,
            -0.442,
            0.517,
            -0.273,
            0.608,
            -0.184,
            0.439,
        ],
        dtype=float,
    ).reshape(12, 2, order="F")
    y8 = np.array([-0.31, 0.52, -0.18, 0.44, -0.67, 0.29, -0.05, 0.61], dtype=float)
    x8 = np.array([-0.2, 0.4, -0.6, 0.8, -0.1, 0.3, -0.5, 0.7], dtype=float).reshape(8, 1, order="F")
    xk8 = np.array(
        [
            0.11,
            -0.22,
            0.33,
            -0.44,
            0.55,
            -0.66,
            0.77,
            -0.88,
            0.19,
            -0.28,
            0.37,
            -0.46,
            0.59,
            -0.68,
            0.79,
            -0.87,
        ],
        dtype=float,
    ).reshape(8, 2, order="F")
    y5 = np.arange(1, 6, dtype=float)
    x5 = np.arange(1, 16, dtype=float).reshape(5, 3, order="F")
    parts = [
        forward(y12, x12),
        forward(y12, x12, xkept=xk12, intercept=False, nvar=3),
        forward(y12, x12, xkept=xk12, intercept=True, nvar=4),
        forward(y8, x8),
        forward(y8, x8, xkept=xk8, intercept=False, nvar=3),
        forward(y8, x8, xkept=xk8, intercept=True, nvar=4),
        forward(y5, x5, intercept=False, nvar=0),
        forward(y5, x5, intercept=True, nvar=1),
        forward(y5, x5, intercept=False, nvar=1),
    ]
    return np.concatenate([np.asarray(part, dtype=float) for part in parts])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join("%.17g" % float(v) for v in np.asarray(value, dtype=float)))
print("MS")
print("%.17g" % statistics.median(elapsed))
