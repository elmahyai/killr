import importlib.util
import statistics
import sys
import time
from pathlib import Path

import numpy as np

_pkg = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_pkg))

_spec = importlib.util.spec_from_file_location(
    "class_prior_probs", _pkg / "mclust" / "class_prior_probs.py"
)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
classPriorProbs = _mod.classPriorProbs

proof_dir = Path(__file__).resolve().parent


def make_fit():
    models = {}
    for nm in ("setosa", "versicolor"):
        mean = np.loadtxt(proof_dir / f"classPriorProbs_mean_{nm}.csv").reshape(-1, 1)
        chol = np.loadtxt(proof_dir / f"classPriorProbs_chol_{nm}.csv")
        models[nm] = {
            "n": 50,
            "G": 1,
            "modelName": "EEE",
            "parameters": {
                "pro": np.array([1.0]),
                "mean": mean,
                "variance": {"d": 4, "G": 1, "cholSigma": chol},
            },
        }
    prop = np.loadtxt(proof_dir / "classPriorProbs_prop.csv")
    return {
        "type": "EDDA",
        "n": 100,
        "d": 4,
        "data": np.loadtxt(proof_dir / "classPriorProbs_data.csv"),
        "prop": {"setosa": float(prop[0]), "versicolor": float(prop[1])},
        "models": models,
    }


fit = make_fit()


def one():
    return list(classPriorProbs(fit))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
