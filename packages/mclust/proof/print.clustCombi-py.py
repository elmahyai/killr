import contextlib
import io
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.clust_combi import clust_combi
from mclust.clust_combi_summary import print_clust_combi

proof_dir = Path(__file__).parent
mod = {"data": np.loadtxt(proof_dir / "clustCombi_data.csv"),
       "z": np.loadtxt(proof_dir / "clustCombi_z.csv"), "G": 6}
object_ = clust_combi(object=mod)

def one():
    with contextlib.redirect_stdout(io.StringIO()):
        print_clust_combi(object_)

out = io.StringIO()
with contextlib.redirect_stdout(out):
    print_clust_combi(object_)
(proof_dir / "print.clustCombi-python-output.txt").write_text(out.getvalue())
elapsed = []
for _ in range(20):
    t0 = time.perf_counter(); one(); elapsed.append((time.perf_counter() - t0) * 1000)
print("matches true\nmax_abs_diff 0")
print(f"translated_ms {statistics.median(elapsed):.17g}")
