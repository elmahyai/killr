import csv
import sys
from pathlib import Path

import numpy as np

_pkg_root = Path(__file__).resolve().parents[1]
_repo_packages = _pkg_root.parent
sys.path.insert(0, str(_repo_packages / "extraDistr"))
sys.path.insert(0, str(_repo_packages / "boot"))
sys.path.insert(0, str(_pkg_root))
from statmod.randomized_block import randomized_block


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
out = randomized_block("Y~SG+VP+V10+EP", random=petrol["No"], data=petrol)
table = np.column_stack([out["varcomp"], out["se.varcomp"]])
with np.printoptions(precision=7, suppress=True):
    print(table)
