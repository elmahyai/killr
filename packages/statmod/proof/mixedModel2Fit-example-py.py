import csv
import sys
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
from statmod.mixed_model2_fit import mixed_model2_fit


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


petrol = _load_petrol()
frame, intercept, terms = _model_frame("Y~SG+VP+V10+EP", petrol["No"], petrol)
y = _model_response(frame, "Y~SG+VP+V10+EP")
x = _model_matrix(frame, "Y~SG+VP+V10+EP", intercept, terms)
z = _random_design(np.asarray(frame["(random)"]))
out = mixed_model2_fit(y, x, z)
table = np.column_stack([out["varcomp"], out["se.varcomp"]])
with np.printoptions(precision=7, suppress=True):
    print(table)
