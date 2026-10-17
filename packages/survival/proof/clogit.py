import statistics
import time
from pathlib import Path

import numpy as np

from survival.clogit import clogit
from survival.fromtimeline import Categorical


def _load_logan2():
    csv_path = Path(__file__).with_name("clogit.logan2.csv")
    if not csv_path.is_file():
        raise FileNotFoundError("proof/clogit.logan2.csv missing")
    import csv

    with csv_path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _frame(rows):
    occ_levels = ["craftsmen", "farm", "operatives", "professional", "sales"]
    occ2_levels = list(occ_levels)
    race_levels = ["non-black", "black"]
    return {
        "occupation": Categorical([r["occupation"] for r in rows], occ_levels),
        "education": [float(r["education"]) for r in rows],
        "race": Categorical([r["race"] for r in rows], race_levels),
        "occ2": Categorical([r["occ2"] for r in rows], occ2_levels),
        "id": [int(r["id"]) for r in rows],
        "y": [int(r["y"]) for r in rows],
    }


def one():
    fit = clogit("y ~ occ2 + occ2:education + occ2:race + strata(id)", _frame(_load_logan2()))
    coef = np.asarray(list(fit["coefficients"].values()), dtype=float)
    loglik = np.asarray(fit["loglik"], dtype=float)
    out = []
    for v in np.concatenate([coef, loglik]):
        out.append("NA" if v != v else f"{v:.17g}")
    return out


if __name__ == "__main__":
    value = one()
    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        one()
        elapsed.append((time.perf_counter() - started) * 1000)
    print("\n".join(value))
    print("MS")
    print(f"{statistics.median(elapsed):.17g}")
