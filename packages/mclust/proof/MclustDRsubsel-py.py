"""Python proof for MclustDRsubsel, against R (MclustDRsubsel-r.R).

Cases A and B: banknote -> translated Mclust (G = 3, VEI) -> mclust_dr(lambda = 0.7)
-> MclustDRsubsel (Mclust path). Case C: the EDDA fixture of MclustDRsubsel_classif
-> MclustDRsubsel (classification path, now run without R).

Timing: one untimed call, then the median of 20 calls (time.perf_counter()).
Speedup = R time / Python time. Run with the project venv from packages/mclust.
"""

import contextlib
import csv
import io
import statistics
import sys
import time
from pathlib import Path

import numpy as np

PROOF = Path(__file__).resolve().parent
PKG = PROOF.parent
sys.path.insert(0, str(PKG))

from mclust.mclust_dr import mclust_dr  # noqa: E402
from mclust.mclust_dr_subsel import MclustDRsubsel  # noqa: E402
from mclust.mclust_object import Mclust  # noqa: E402
from mclust.print_mclust_dr import print_MclustDRsubsel  # noqa: E402

# A: G = 1:3, VEI/EEE. B: default G = 1:9 and all default models (R's defaults).
# C: EDDA classification path, G = 1:2, EEE/VEI.
CASES = {
    "A": dict(g=[1, 2, 3], model_names=["VEI", "EEE"]),
    "B": dict(),
    "C": dict(g=[1, 2], model_names=["EEE", "VEI"]),
}


def read_banknote() -> np.ndarray:
    with (PROOF / "MclustDRsubsel_banknote4.csv").open(newline="") as handle:
        rows = list(csv.reader(handle))[1:]
    return np.asarray([[float(v) for v in row] for row in rows], dtype=float)


def read_matrix(path: Path) -> np.ndarray:
    with path.open(newline="") as handle:
        return np.asarray([[float(x) for x in row] for row in csv.reader(handle)], dtype=float)


def build_mclust_dr() -> dict:
    mod = Mclust(read_banknote(), G=3, modelNames="VEI")
    return mclust_dr(mod, lambda_=0.7)


def build_classif_dr() -> dict:
    meta = (PROOF / "MclustDRsubsel_classif_meta.txt").read_text().splitlines()
    labels = [line.strip().strip('"') for line in (PROOF / "MclustDRsubsel_classif_cl.csv").read_text().splitlines() if line.strip()]
    return {
        "type": meta[2],
        "x": read_matrix(PROOF / "MclustDRsubsel_classif_x.csv"),
        "dir": read_matrix(PROOF / "MclustDRsubsel_classif_dir.csv"),
        "numdir": int(meta[0]),
        "lambda": float(meta[1]),
        "classification": np.asarray(labels, dtype=object),
    }


def factor_codes(values) -> np.ndarray:
    """R as.numeric(factor(x)): codes from the sorted levels."""
    arr = np.asarray(values, dtype=object).reshape(-1)
    try:
        levels = sorted({float(v) for v in arr})
        index = {v: i + 1 for i, v in enumerate(levels)}
        return np.asarray([index[float(v)] for v in arr], dtype=float)
    except (TypeError, ValueError):
        levels = sorted({str(v) for v in arr})
        index = {v: i + 1 for i, v in enumerate(levels)}
        return np.asarray([index[str(v)] for v in arr], dtype=float)


def flatten(sub) -> np.ndarray:
    k = int(sub["numdir"])
    direction = np.asarray(sub["dir"], dtype=float)[:, :k]
    return np.concatenate([
        [float(k), float(sub["lambda"])],
        direction.reshape(-1, order="F"),
        np.asarray(sub["basisx"], dtype=float).reshape(-1, order="F"),
        np.asarray(sub["std.basisx"], dtype=float).reshape(-1, order="F"),
        factor_codes(sub["classification"]),
    ])


def read_ref(path: Path) -> tuple[float, np.ndarray]:
    lines = path.read_text().splitlines()
    r_ms = float(lines[0].split()[1])
    return r_ms, np.asarray([float(x) for x in lines[1:]], dtype=float)


mclust_dr_obj = build_mclust_dr()
classif_dr_obj = build_classif_dr()
for case_id, kwargs in CASES.items():
    dr = classif_dr_obj if case_id == "C" else mclust_dr_obj

    def one():
        return MclustDRsubsel(dr, verbose=False, **kwargs)

    sub = one()  # untimed call
    value = flatten(sub)
    r_ms, ref = read_ref(PROOF / f"MclustDRsubsel-{case_id}-r-values.txt")
    max_abs = float("inf") if value.shape != ref.shape else float(np.max(np.abs(value - ref)))
    matches = max_abs <= 1e-8

    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        one()
        elapsed.append((time.perf_counter() - started) * 1000)
    translated_ms = statistics.median(elapsed)

    codes = factor_codes(sub["classification"]).astype(int)
    groups = "/".join(str(c) for c in np.bincount(codes)[1:])
    print(f"case {case_id}")
    print(f"matches {'true' if matches else 'false'}")
    print(f"max_abs_diff {max_abs:.17g}")
    print(f"groups {groups}")
    print(f"r_ms {r_ms:.17g}")
    print(f"translated_ms {translated_ms:.17g}")
    print(f"speedup {r_ms / translated_ms:.17g}")

    if case_id == "A":
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            print_MclustDRsubsel(sub)
        (PROOF.parent / "docs" / "output" / "MclustDRsubsel-python.txt").write_text(out.getvalue())
