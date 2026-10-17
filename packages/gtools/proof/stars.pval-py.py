import json
import statistics
import sys
import time

import numpy as np

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "stars_pval",
    "/home/ahmed/killr_projects/killr/packages/gtools/gtools/stars_pval.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
stars_pval = _mod.stars_pval


def flat_stars(result):
    flat = result.values.ravel(order="F")
    return "|".join(flat)


def one():
    p = np.array(
        [
            0.0004,
            0.0015,
            0.013,
            0.044,
            0.067,
            0.24,
            np.nan,
            0.0,
            0.001,
            0.01,
            0.05,
            0.1,
            1.0,
            1e-10,
            0.000999999,
            0.0010000001,
            0.009999999,
            0.0100000001,
        ],
        dtype=float,
    )
    ex = stars_pval(p)
    m = stars_pval(
        np.array([0.001, 0.02, 0.06, 0.11], dtype=float).reshape(2, 2, order="F")
    )
    empty = stars_pval(np.array([], dtype=float))
    empty_mat = stars_pval(np.zeros((0, 3), dtype=float))
    return "§".join(
        [
            flat_stars(ex),
            ex.legend,
            flat_stars(m),
            m.legend,
            flat_stars(empty),
            flat_stars(empty_mat),
            str(empty_mat.values.size),
        ]
    )


stars_pval(np.array([0.5]))
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
