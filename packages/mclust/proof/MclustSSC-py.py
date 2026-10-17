import csv
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.mclust_ssc import mclust_ssc

PROOF = Path("/home/ahmed/killr_projects/killr/packages/mclust/proof")


def _load_case():
    x = np.loadtxt(PROOF / "MclustSSC_X.csv", delimiter=",", skiprows=1)
    with (PROOF / "MclustSSC_class.csv").open(newline="") as handle:
        cl = []
        for row in csv.DictReader(handle):
            v = row["class"]
            if v in ("", "NA"):
                cl.append(float("nan"))
            else:
                cl.append(v)
    return x, cl


def flatten(mod) -> list[float]:
    pro = np.asarray(mod["parameters"]["pro"], dtype=float)
    mean = np.asarray(mod["parameters"]["mean"], dtype=float)
    z = np.asarray(mod["z"], dtype=float)
    return [
        float(mod["G"]),
        float(mod["loglik"]),
        float(mod["df"]),
        float(mod["bic"]),
        *z.reshape(-1, order="F").tolist(),
        *pro.reshape(-1, order="F").tolist(),
        *mean.reshape(-1, order="F").tolist(),
    ]


def one() -> list[float]:
    x, cl = _load_case()
    mod = mclust_ssc(x, cl, verbose=False)
    return flatten(mod)


if __name__ == "__main__":
    value = one()
    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        one()
        elapsed.append((time.perf_counter() - started) * 1000)
    for item in value:
        print("%.17g" % item)
    print("%.17g" % statistics.median(elapsed))
