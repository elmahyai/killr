"""Proof for MclustDR on the banknote Mclust fit (G = 3, VEI, lambda = 0.7).

Compares every numeric field of the translated MclustDR result with R:
numdir, lambda, evalues, dir, basis, std.basis, M, M.I, M.II, pro,
class2mixcomp, mixcomp and classification (the per-observation labels, as
R's factor codes). The R values come from MclustDR-r.R.

Timing: median of 20 calls of ``mclust_dr`` on the already-loaded fit, which
matches the R timing of ``MclustDR(mod, lambda = 0.7)``.
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

import numpy as np

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF.parent))
sys.path.insert(0, str(PROOF))

from _mclust_dr_fit_fixture import load_mod  # noqa: E402
from mclust.mclust_dr import mclust_dr  # noqa: E402

DOCS = PROOF.parent / "docs" / "output"
TOL = 1e-8


def _flat(dr) -> np.ndarray:
    parts = [
        [float(dr["numdir"])],
        [float(dr["lambda"])],
        np.asarray(dr["evalues"], dtype=float).ravel(order="F"),
        np.asarray(dr["dir"], dtype=float).ravel(order="F"),
        np.asarray(dr["basis"], dtype=float).ravel(order="F"),
        np.asarray(dr["std.basis"], dtype=float).ravel(order="F"),
        np.asarray(dr["M"], dtype=float).ravel(order="F"),
        np.asarray(dr["M.I"], dtype=float).ravel(order="F"),
        np.asarray(dr["M.II"], dtype=float).ravel(order="F"),
        np.asarray(dr["pro"], dtype=float).ravel(order="F"),
        np.asarray(dr["class2mixcomp"], dtype=float).ravel(order="F"),
        np.asarray(dr["mixcomp"], dtype=float).ravel(order="F"),
        np.asarray(dr["classification"], dtype=float).ravel(order="F"),
    ]
    return np.concatenate([np.asarray(p, dtype=float) for p in parts])


def one(mod):
    return mclust_dr(mod, lambda_=0.7)


mod = load_mod()

# untimed call: values
value = _flat(one(mod))
ref = np.loadtxt(PROOF / "MclustDR-r-values.txt")
if value.shape != ref.shape:
    max_abs = float("inf")
else:
    max_abs = float(np.max(np.abs(value - ref)))
matches = max_abs <= TOL

# classification alone, compared as exact integers in the same order
dr = one(mod)
cls_py = np.asarray(dr["classification"]).astype(int)
n_obs = len(cls_py)
cls_ref = ref[-n_obs:].astype(int)
cls_exact = bool(np.array_equal(cls_py, cls_ref))

print(f"matches {'yes' if matches else 'no'}")
print(f"classification_exact {'yes' if cls_exact else 'no'}")
print(f"classification_type {type(dr['classification']).__name__} {np.asarray(dr['classification']).dtype}")
print(f"max_abs_diff {max_abs:.17g}")

# timed: median of 20 calls
timed = []
for _ in range(20):
    started = time.perf_counter()
    one(mod)
    timed.append((time.perf_counter() - started) * 1000)
r_ms = float((PROOF / "MclustDR-r-ms.txt").read_text())
t_ms = statistics.median(timed)
print(f"r_ms {r_ms:.17g}")
print(f"translated_ms {t_ms:.17g}")
print(f"speedup {r_ms / t_ms:.17g}")

(DOCS / "MclustDR-python.txt").write_text(
    "\n".join(f"{v:.17g}" for v in value) + "\n"
)
(DOCS / "MclustDR-compare.txt").write_text(
    "\n".join([
        f"matches {'yes' if matches else 'no'}",
        f"classification_exact {'yes' if cls_exact else 'no'}",
        f"max_abs_diff {max_abs:.17g}",
        f"r_ms {r_ms:.17g}",
        f"translated_ms {t_ms:.17g}",
        f"speedup {r_ms / t_ms:.17g}",
        f"values_compared {value.size}",
        "",
    ])
)
