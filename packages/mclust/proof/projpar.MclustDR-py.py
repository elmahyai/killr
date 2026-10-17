import csv
import importlib.util
import statistics
import time
from pathlib import Path

import numpy as np

PROOF = Path("/home/ahmed/killr_projects/killr/packages/mclust/proof")
_spec = importlib.util.spec_from_file_location(
    "projpar_mclust_dr",
    PROOF.parent / "mclust" / "projpar_mclust_dr.py",
)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
projpar_MclustDR = _mod.projpar_MclustDR

_dr_spec = importlib.util.spec_from_file_location(
    "mclust_dr",
    PROOF.parent / "mclust" / "mclust_dr.py",
)
_dr_mod = importlib.util.module_from_spec(_dr_spec)
assert _dr_spec.loader is not None
_dr_spec.loader.exec_module(_dr_mod)
mclust_dr = _dr_mod.mclust_dr


def _read_matrix(path: Path) -> np.ndarray:
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        if header and not _is_numeric_row(header):
            rows = [[float(x) for x in row] for row in reader]
        else:
            rows = [[float(x) for x in header]]
            rows.extend([[float(x) for x in row] for row in reader])
    return np.asarray(rows, dtype=float)


def _is_numeric_row(row: list[str]) -> bool:
    try:
        [float(x) for x in row]
    except ValueError:
        return False
    return True


def _load_mod() -> dict:
    data = _read_matrix(PROOF / "MclustDR_data.csv")
    mean = _read_matrix(PROOF / "MclustDR_mean.csv")
    p, g = mean.shape
    sigma = np.stack(
        [_read_matrix(path) for path in sorted(PROOF.glob("MclustDR_sigma_*.csv"))],
        axis=2,
    )
    with (PROOF / "MclustDR_classification.csv").open(newline="") as handle:
        rows = list(csv.reader(handle))
        start = 1 if rows and not _is_numeric_row(rows[0]) else 0
        classification = np.asarray([int(float(row[0])) for row in rows[start:]])
    with (PROOF / "MclustDR_pro.csv").open(newline="") as handle:
        rows = list(csv.reader(handle))
        start = 1 if rows and not _is_numeric_row(rows[0]) else 0
        pro = np.asarray([float(row[0]) for row in rows[start:]])
    meta_lines = (PROOF / "MclustDR_meta.txt").read_text().splitlines()
    return {
        "data": data,
        "G": int(meta_lines[0]),
        "modelName": meta_lines[1],
        "hypvol": float(meta_lines[2]) if meta_lines[2] != "NA" else float("nan"),
        "classification": classification,
        "parameters": {
            "pro": pro,
            "mean": mean,
            "variance": {"sigma": sigma},
        },
    }


def _flatten_par(par: dict) -> list[float]:
    return [
        *np.asarray(par["mean"], dtype=float).reshape(-1, order="F").tolist(),
        *np.asarray(par["variance"], dtype=float).reshape(-1, order="F").tolist(),
    ]


def one() -> list[float]:
    dr = mclust_dr(_load_mod(), lambda_=0.7)
    p1 = projpar_MclustDR(dr)
    p2 = projpar_MclustDR(dr, dim=(1, 2), center=True, raw=False)
    p3 = projpar_MclustDR(dr, dim=(1,), center=False, raw=True)
    return _flatten_par(p1) + _flatten_par(p2) + _flatten_par(p3)


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
