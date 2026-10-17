import statistics, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.mstep_eee_ev_vv import mstepVVV
i = np.arange(1, 25, dtype=float)
x = np.column_stack([i / 10 + i % 5, i * (i % 7) / 3 - i / 20, i * 3 / 2 + i / 50])
raw = np.column_stack([1 + ((i + 2 * g) % 3) for g in (1, 2)])
z = raw / raw.sum(axis=1, keepdims=True)
def flat(r):
    v = r["parameters"]["variance"]
    return np.concatenate([np.asarray(a, dtype=float).ravel(order="F") for a in
                           (r["parameters"]["pro"], r["parameters"]["mean"], v["sigma"])])
def one(): return flat(mstepVVV(x, z))
value = one(); times = []
for _ in range(20):
    t0 = time.perf_counter(); one(); times.append((time.perf_counter() - t0) * 1000)
print("\n".join("%.17g" % v for v in value)); print("%.17g" % statistics.median(times))
