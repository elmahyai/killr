import math, statistics, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.mvn import mvnXXI
OUT = Path(__file__).resolve().parents[1] / "docs" / "output"
cases = {
    "nonsingular": np.array([[-1.2,.5,2.1,1.7],[-.3,.9,3.2,1.1],[.4,-.8,1.3,2.6],[2.2,1.5,-1.1,.7],[1.1,-1.7,.2,3.4],[3.3,.2,2.4,-.5]]),
    "singular": np.array([[0.,1.,2.,3.],[0.,2.,3.,4.],[0.,3.,4.,5.]]),
}
def value(x):
    with np.errstate(divide="ignore", invalid="ignore"):
        y = mvnXXI(x); v = y["parameters"]["variance"]
    return np.r_[y["parameters"]["mean"].ravel(), v["scale"], v["shape"], y["loglik"]]
def one():
    for x in cases.values():
        value(x)
reference = (OUT / "mvnXXI-r.txt").read_text().splitlines()
lines = []
max_diff = 0.0
matches = True
pos = 0
for name, x in cases.items():
    got = value(x)
    lines += [f"CASE {name}", *("%.17g" % v if not math.isnan(v) else "NA" for v in got)]
    assert reference[pos] == f"CASE {name}"
    pos += 1
    expected = []
    while not reference[pos].startswith(("CASE ", "r_ms ")):
        expected.append(float(reference[pos]) if reference[pos] != "NA" else math.nan)
        pos += 1
    # The proof criterion is the density/log-density, including NA positions.
    for a, b in zip(expected[-1:], got[-1:]):
        if math.isnan(a) != math.isnan(b):
            matches = False
        elif not math.isnan(a):
            max_diff = max(max_diff, abs(a - b))
            matches = matches and abs(a - b) <= 1e-8
    matches = matches and len(expected) == len(got)
one()
elapsed = []
for _ in range(20):
    t0 = time.perf_counter(); one(); elapsed.append((time.perf_counter() - t0) * 1000)
translated_ms = statistics.median(elapsed)
lines.append("translated_ms %.17g" % translated_ms)
(OUT / "mvnXXI-py.txt").write_text("\n".join(lines) + "\n")
r_ms = float(reference[-1].split()[1])
print(f"matches {'yes' if matches else 'no'}")
print(f"max_abs_diff {max_diff:.17g}")
print(f"r_ms {r_ms:.17g}")
print(f"translated_ms {translated_ms:.17g}")
print(f"speedup {r_ms / translated_ms:.17g}")
