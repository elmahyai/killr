import json
import sys
import time
import numpy as np

sys.path.insert(0, "packages/estimability")
from estimability.estimability import (
    all_estble, estble_subspace, is_estble, legacy_nonest_basis,
    nonest_basis, nonest_basis_svd,
)

X = np.array([[1., 0., 1., 1.], [1., 1., 2., 3.], [1., 2., 3., 5.]])
L = np.array([[1., 2., 3., 5.], [0., 1., -1., 0.]])
_, _, vt = np.linalg.svd(X, full_matrices=True)
svd = {"d": np.linalg.svd(X, full_matrices=False, compute_uv=False), "v": vt.T}
def run():
    M = np.array([[1., 0., 0.], [1., 1., 1.], [1., 2., 2.]])
    model = {
        "design_matrix": lambda d: M if d is None else np.asarray(d, dtype=float),
        "predict": lambda d, **k: np.sum(np.asarray(d, dtype=float), axis=1),
    }
    updated = __import__("estimability.estimability", fromlist=["eupdate"]).eupdate(model)
    return {
        "all_estble": bool(is_estble([1., 2.], all_estble)),
        "basis": nonest_basis(X).tolist(),
        "svd_basis": nonest_basis_svd(svd).tolist(),
        "legacy": legacy_nonest_basis(X).tolist(),
        "estimable": np.asarray(is_estble(L, nonest_basis(X))).tolist(),
        "subspace": estble_subspace(L, nonest_basis(X)).tolist(),
        "epredict": __import__("estimability.estimability", fromlist=["epredict"]).epredict(
            updated, M, type="estimability"
        ).tolist(),
        "eupdate": updated["nonest"].tolist(),
    }
run()
t = []
for _ in range(20):
    a = time.perf_counter(); run(); t.append((time.perf_counter() - a) * 1000)
print(json.dumps({"result": run(), "ms": float(np.median(t))}, allow_nan=True))
