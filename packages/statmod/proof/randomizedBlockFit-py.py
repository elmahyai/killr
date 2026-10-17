import csv
import statistics
import sys
import time
from pathlib import Path

import numpy as np

_pkg_root = Path(__file__).resolve().parents[1]
_repo_packages = _pkg_root.parent
sys.path.insert(0, str(_repo_packages / "extraDistr"))
sys.path.insert(0, str(_repo_packages / "boot"))
sys.path.insert(0, str(_pkg_root))
from statmod.mixed_model2 import (
    _model_frame,
    _model_matrix,
    _model_response,
    _random_design,
)
from statmod.mixed_model2_fit import randomized_block_fit


def _load_petrol() -> dict:
    csv_path = Path(__file__).resolve().parent / "mixedModel2-petrol.csv"
    with csv_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        petrol = {name: [] for name in reader.fieldnames}
        for row in reader:
            for name, value in row.items():
                if name == "No":
                    petrol[name].append(value)
                else:
                    petrol[name].append(float(value))
    return petrol


def petrol_mats():
    petrol = _load_petrol()
    frame, intercept, terms = _model_frame(
        "Y~SG+VP+V10+EP", petrol["No"], petrol
    )
    y = _model_response(frame, "Y~SG+VP+V10+EP")
    x = _model_matrix(frame, "Y~SG+VP+V10+EP", intercept, terms)
    z = _random_design(np.asarray(frame["(random)"]))
    return y, x, z


def collect(out: dict) -> np.ndarray:
    if "se.varcomp" not in out:
        return np.asarray(out["varcomp"], dtype=float)
    return np.concatenate(
        [
            out["varcomp"],
            out["se.varcomp"],
            out["coefficients"],
            out["se.coefficients"],
        ]
    )


def one() -> np.ndarray:
    y, x, z = petrol_mats()
    out = randomized_block_fit(y, x, z)
    out2 = randomized_block_fit(y, x, z, only_varcomp=True)
    return np.concatenate([collect(out), collect(out2)])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join("%.17g" % float(v) for v in value))
print("MS")
print("%.17g" % statistics.median(elapsed))
