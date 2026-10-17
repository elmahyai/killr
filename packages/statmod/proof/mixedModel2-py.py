import csv
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from statmod.mixed_model2 import mixed_model2


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
    petrol = _load_petrol()
    out = mixed_model2("Y~SG+VP+V10+EP", random=petrol["No"], data=petrol)
    out2 = mixed_model2(
        "Y~SG+VP+V10+EP",
        random=petrol["No"],
        data=petrol,
        only_varcomp=True,
    )
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
