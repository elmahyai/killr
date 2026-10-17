import importlib.util
import statistics
import sys
import time
from pathlib import Path

import numpy as np

_pkg = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_pkg))


def _load(name, rel):
    path = _pkg / "mclust" / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_clust_combi = _load("clust_combi_mod", "clust_combi.py")
_clust_combi_optim = _load("clust_combi_optim_mod", "clust_combi_optim.py")
clust_combi = _clust_combi.clust_combi
clustCombiOptim = _clust_combi_optim.clustCombiOptim

proof_dir = Path(__file__).resolve().parent
G = 6
mod = {
    "data": np.loadtxt(proof_dir / "clustCombi_data.csv"),
    "z": np.loadtxt(proof_dir / "clustCombi_z.csv"),
    "G": G,
}
cc = clust_combi(object=mod)


def flatten(out):
    return [out["numClusters.combi"], *out["z.combi"].reshape(-1, order="F"), *out["cluster.combi"]]


def one():
    return flatten(clustCombiOptim(cc, reg=2, plot=False))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
