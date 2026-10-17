import importlib.util
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_spec = importlib.util.spec_from_file_location(
    "combi_tree", Path(__file__).resolve().parents[1] / "mclust" / "combi_tree.py"
)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
combiTree = _mod.combiTree

proof_dir = Path(__file__).resolve().parent
G = 6
mod = {
    "data": np.loadtxt(proof_dir / "clustCombi_data.csv"),
    "z": np.loadtxt(proof_dir / "clustCombi_z.csv"),
    "G": G,
}


def flatten_hc(hc):
    return list(np.asarray(hc["merge"]).reshape(-1, order="F")) + list(hc["height"]) + list(
        hc["order"]
    )


_clust_combi = importlib.util.spec_from_file_location(
    "clust_combi_mod", Path(__file__).resolve().parents[1] / "mclust" / "clust_combi.py"
)
_cc_mod = importlib.util.module_from_spec(_clust_combi)
assert _clust_combi.loader is not None
_clust_combi.loader.exec_module(_cc_mod)
cc = _cc_mod.clust_combi(object=mod)


def one():
    hc = combiTree(cc, yaxis="entropy")
    return flatten_hc(hc)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
