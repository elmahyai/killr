import importlib.util
import statistics
import sys
import time
from pathlib import Path

import numpy as np

pkg = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pkg))
spec = importlib.util.spec_from_file_location(
    "predict_mclust_da", pkg / "mclust" / "predict_mclust_da.py"
)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)
predict_mclust_da = mod.predict_mclust_da


def make_mclust_da():
    sigma = np.array([[1.2, 0.25], [0.25, 0.8]])
    chol = np.linalg.cholesky(sigma)

    def model(mean):
        return {
            "n": 50,
            "modelName": "EEE",
            "G": 1,
            "parameters": {
                "pro": np.array([1.0]),
                "mean": np.asarray(mean, dtype=float).reshape(2, 1),
                "variance": {
                    "modelName": "EEE",
                    "d": 2,
                    "G": 1,
                    "sigma": sigma[:, :, None],
                    "Sigma": sigma,
                    "cholSigma": chol,
                },
            },
        }

    return {
        "models": {"alpha": model([0, 0]), "beta": model([3, 2])},
        "prop": {"alpha": 0.3, "beta": 0.7},
        "data": np.array([[0, 0], [1, 1], [2, 1], [3, 2], [4, 3], [-1, 0]], dtype=float),
        "type": "MclustDA",
        "n": 6,
        "d": 2,
    }


fit = make_mclust_da()
newdata = np.array([[-1, 0], [0, 0], [1, 1], [2, 1], [3, 2], [4, 3]], dtype=float)


def one():
    return predict_mclust_da(fit, newdata=newdata)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value["classification"]:
    print(item)
for item in value["z"].reshape(-1, order="F"):
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
