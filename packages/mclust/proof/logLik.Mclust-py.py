import csv
import importlib.util
import statistics
import time
from pathlib import Path

import numpy as np

PROOF = Path("/home/ahmed/killr_projects/killr/packages/mclust/proof")
_spec = importlib.util.spec_from_file_location(
    "loglik_mclust",
    PROOF.parent / "mclust" / "loglik_mclust.py",
)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
logLik_Mclust = _mod.logLik_Mclust


def _read_matrix(path: Path) -> np.ndarray:
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        try:
            [float(x) for x in header]
            rows = [[float(x) for x in header]]
        except ValueError:
            rows = []
        rows.extend([[float(x) for x in row] for row in reader])
    return np.asarray(rows, dtype=float)


def _load_mod() -> dict:
    data = _read_matrix(PROOF / "MclustDR_data.csv")
    mean = _read_matrix(PROOF / "MclustDR_mean.csv")
    meta_lines = (PROOF / "logLik_meta.txt").read_text().splitlines()
    loglik, df, n, d = (float(meta_lines[i]) for i in range(4))
    with (PROOF / "MclustDR_pro.csv").open(newline="") as handle:
        rows = list(csv.reader(handle))
        pro = np.asarray([float(row[0]) for row in rows[1:]])
    hypvol_line = (PROOF / "MclustDR_meta.txt").read_text().splitlines()[2]
    hypvol = float("nan") if hypvol_line == "NA" else float(hypvol_line)
    return {
        "data": data,
        "G": int((PROOF / "MclustDR_meta.txt").read_text().splitlines()[0]),
        "modelName": (PROOF / "MclustDR_meta.txt").read_text().splitlines()[1],
        "hypvol": hypvol,
        "loglik": loglik,
        "df": int(df),
        "n": int(n),
        "d": int(d),
        "parameters": {"pro": pro, "mean": mean},
    }


def one() -> np.ndarray:
    ll = logLik_Mclust(_load_mod())
    return np.array([ll.value, ll.df, ll.nobs], dtype=float)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

for item in value:
    print(f"{item:.17g}")
print(f"{statistics.median(elapsed):.17g}")
