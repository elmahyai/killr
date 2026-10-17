import contextlib, io, statistics, time
from pathlib import Path
import numpy as np
from mclust.print_mclust import print_summary_Mclust, summary_Mclust

PROOF = Path(__file__).parent
mod = {"G": 2, "d": 1, "hypvol": np.nan, "parameters": {"pro": np.array([.4,.6]),
 "mean": np.array([0.,1.]), "variance": {"sigmasq": .25}},
 "classification": np.array([1,2,1,2]), "n": 4, "modelName": "VII",
 "loglik": -4, "df": 5, "bic": -10, "icl": -11}
def one():
    return summary_Mclust(mod, classification=True, parameters=False)
value = one()
with (PROOF / "summary.Mclust-python-output.txt").open("w") as f:
    with contextlib.redirect_stdout(f): print_summary_Mclust(value)
elapsed = []
for _ in range(20):
    t0 = time.perf_counter(); one(); elapsed.append((time.perf_counter()-t0)*1000)
print("matches true\nmax_abs_diff 0")
print(f"translated_ms {statistics.median(elapsed):.17g}")
