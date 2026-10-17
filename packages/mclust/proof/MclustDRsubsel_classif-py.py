import importlib.util
import csv
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
PROOF = Path(__file__).resolve().parent

_spec = importlib.util.spec_from_file_location(
    "mclust_dr_subsel_classif",
    PROOF.parent / "mclust" / "mclust_dr_subsel_classif.py",
)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)


def _read_matrix(path: Path) -> np.ndarray:
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        return np.asarray([[float(x) for x in row] for row in reader], dtype=float)


def _load_dr() -> dict:
    meta = (PROOF / "MclustDRsubsel_classif_meta.txt").read_text().splitlines()
    with (PROOF / "MclustDRsubsel_classif_cl.csv").open() as f:
        cl = [line.strip() for line in f if line.strip()]
    return {
        "type": meta[2],
        "x": _read_matrix(PROOF / "MclustDRsubsel_classif_x.csv"),
        "dir": _read_matrix(PROOF / "MclustDRsubsel_classif_dir.csv"),
        "numdir": int(meta[0]),
        "lambda": float(meta[1]),
        "classification": np.asarray(cl, dtype=object),
    }


def one():
    dr = _load_dr()
    out = _mod.MclustDRsubsel_classif(dr, g=[1, 2], model_names=["EEE", "VEI"], verbose=False)
    b = np.asarray(out["basisx"], dtype=float)
    return [float(out["numdir"]), float(out["lambda"]), *b.reshape(-1, order="F").tolist()]


value = one()
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - t0) * 1000)

for item in value:
    print(f"{item:.17g}")
print(f"{statistics.median(elapsed):.17g}")
