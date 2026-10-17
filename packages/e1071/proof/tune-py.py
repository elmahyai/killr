import importlib.util
import json
import statistics
import sys
import time
import types
from pathlib import Path

import numpy as np

ROOT = Path("/home/ahmed/killr_projects/killr")
sys.path[:0] = [
    str(ROOT / "packages/e1071"),
    str(ROOT / "packages/boot"),
    str(ROOT / "crates/svm"),
]

if "e1071" not in sys.modules:
    pkg = types.ModuleType("e1071")
    pkg.__path__ = [str(ROOT / "packages/e1071/e1071")]
    sys.modules["e1071"] = pkg


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / "packages/e1071" / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_load("e1071.tune", "e1071/tune.py")
_load("e1071.scale", "e1071/scale.py")
svm_mod = _load("e1071.svm", "e1071/svm.py")
tuning_mod = _load("e1071.tuning", "e1071/tuning.py")

from boot.rng import set_seed

tune_control = sys.modules["e1071.tune"].tune_control
tune = tuning_mod.tune
_as_matrix = svm_mod._as_matrix
_predict_svm = svm_mod._predict_svm


def predict_svm(model, newdata):
    vals, _ = _predict_svm(model, _as_matrix(newdata))
    lev = model.get("levels")
    if lev is not None and int(model["type"]) < 3:
        return [lev[int(v) - 1] for v in np.asarray(vals).reshape(-1)]
    return list(np.asarray(vals).reshape(-1))


def _summary(res):
    perf = res["performances"]
    return (
        [float(res["best.performance"])]
        + [float(res["best.parameters"]["cost"]), float(res["best.parameters"]["gamma"])]
        + [float(row["error"]) for row in perf]
        + [float(row["dispersion"]) for row in perf]
    )


def case_a():
    # Two classes, 6 rows, 3-fold CV over a 2x2 grid.
    set_seed(4242)
    x = np.array(
        [
            [0.0, 1.0],
            [1.2, 0.8],
            [2.5, 2.7],
            [2.8, 2.4],
            [0.1, 0.9],
            [2.6, 2.5],
        ],
        dtype=float,
    )
    y = ["setosa", "setosa", "versicolor", "versicolor", "setosa", "versicolor"]
    ctrl = tune_control(cross=3, best_model=False, performances=True)
    res = tune(
        "svm",
        x,
        y,
        ranges={"cost": [0.5, 1.0], "gamma": [0.3, 0.5]},
        predict_func=predict_svm,
        tunecontrol=ctrl,
        kernel="radial",
        scale=True,
        cross=0,
    )
    return _summary(res)


def case_b():
    # Three classes, first-appearance order differs from sorted level order.
    # n = 7 with 3 folds puts integers on the fold breaks (1, 3, 5, 7).
    # 2 x 3 grid: expand.grid(list(cost, gamma)) varies cost fastest. Errors
    # differ across the grid, so a wrong row order changes the compared vectors.
    set_seed(4242)
    x = np.array(
        [
            [2.6, 2.4],
            [0.1, 0.3],
            [1.4, 1.1],
            [2.9, 2.2],
            [0.4, 0.0],
            [1.1, 1.6],
            [0.0, 0.6],
        ],
        dtype=float,
    )
    y = ["virginica", "setosa", "versicolor", "virginica", "setosa", "versicolor", "setosa"]
    ctrl = tune_control(cross=3, best_model=False, performances=True)
    res = tune(
        "svm",
        x,
        y,
        ranges={"cost": [0.5, 4.0], "gamma": [0.2, 1.0, 3.0]},
        predict_func=predict_svm,
        tunecontrol=ctrl,
        kernel="radial",
        scale=True,
        cross=0,
    )
    return _summary(res)


def one():
    return case_a() + case_b()


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
