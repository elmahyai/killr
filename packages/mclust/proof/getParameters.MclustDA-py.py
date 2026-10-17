import importlib.util
import statistics
import time

import numpy as np

_spec = importlib.util.spec_from_file_location(
    "get_parameters_mclust_da",
    "/home/ahmed/killr_projects/killr/packages/mclust/mclust/get_parameters_mclust_da.py",
)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
getParameters_MclustDA = _mod.getParameters_MclustDA


def make_min_mclust_da():
    return {
        "type": "EDDA",
        "n": 100,
        "d": 4,
        "models": {
            "setosa": {
                "n": 50,
                "G": 1,
                "modelName": "EEE",
                "parameters": {
                    "pro": np.array([1.0]),
                    "mean": np.array([[5.0], [6.0], [7.0], [8.0]], dtype=float),
                    "variance": {
                        "d": 4,
                        "G": 1,
                        "sigma": np.diag([0.1, 0.2, 0.3, 0.4]).reshape(4, 4, 1, order="F"),
                        "Sigma": np.diag([0.1] * 4),
                    },
                },
            },
            "versicolor": {
                "n": 50,
                "G": 1,
                "modelName": "EEE",
                "parameters": {
                    "pro": None,
                    "mean": np.array([[9.0], [10.0], [11.0], [12.0]], dtype=float),
                    "variance": {
                        "d": 4,
                        "G": 1,
                        "sigma": np.diag([0.5, 0.6, 0.7, 0.8]).reshape(4, 4, 1, order="F"),
                        "Sigma": np.diag([0.5] * 4),
                    },
                },
            },
        },
    }


def flatten_get_parameters(par):
    out = [len(par)]
    for el in par:
        if isinstance(el, dict):
            pro = el.get("pro")
            if pro is not None:
                out.extend(np.asarray(pro, dtype=float).reshape(-1).tolist())
            out.extend(np.asarray(el["mean"], dtype=float, order="F").reshape(-1).tolist())
            out.extend(np.asarray(el["variance"], dtype=float, order="F").reshape(-1).tolist())
        else:
            out.append(float(el))
    return out


def one():
    return flatten_get_parameters(getParameters_MclustDA(make_min_mclust_da()))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
