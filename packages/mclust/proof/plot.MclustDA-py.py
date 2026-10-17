from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF.parent))
from mclust.plot_mclust_da import plot_MclustDA
from mclust.predict_mclust_da import predict_mclust_da

data = np.array([[-1,-1], [-.5,-1], [.5,1], [1,1], [1.5,1], [2,2]], dtype=float)
classes = np.array(["1", "1", "1", "2", "2", "2"], dtype=object)
sigma = np.eye(2)[:, :, None]
def model(mu):
    return {"modelName": "EEE", "n": 3, "d": 2, "G": 1,
            "parameters": {"pro": np.array([1.]), "mean": np.asarray(mu)[:, None],
                           "variance": {"sigma": sigma[:, :, 0],
                                        "Sigma": np.eye(2),
                                        "cholSigma": np.eye(2)}}}
fit = {"data": data, "class": classes, "prop": np.array([.5, .5]),
       "models": [model([-1, -1]), model([1, 1])]}
grid = np.asarray([(x, y) for y in np.linspace(-2, 2, 25)
                    for x in np.linspace(-2, 2, 25)])

def one():
    predicted = predict_mclust_da(fit, grid)["classification"]
    fig, ax = plt.subplots()
    plot_MclustDA(fit, what="classification", ax=ax)
    plt.close(fig)
    return np.r_[np.asarray(predicted, dtype=int),
                 np.asarray(predict_mclust_da(fit, data)["classification"], dtype=int)]

value = one()
times = []
one()
for _ in range(20):
    t0 = time.perf_counter()
    one()
    times.append((time.perf_counter() - t0) * 1000)
out = PROOF.parent / "docs" / "output"
out.mkdir(parents=True, exist_ok=True)
(out / "plot.MclustDA-py.txt").write_text("\n".join(f"{v:.17g}" for v in value) + "\n")
ms = statistics.median(times)
(out / "plot.MclustDA-py-time.txt").write_text(f"{ms:.17g}\n")
fig, ax = plt.subplots(figsize=(6, 6))
plot_MclustDA(fit, what="classification", ax=ax)
fig.savefig(out / "plot.MclustDA-classification-python.svg")
plt.close(fig)
r = float((out / "plot.MclustDA-r-time.txt").read_text())
r_values = np.loadtxt(out / "plot.MclustDA-r.txt")
print(f"matches {'yes' if np.allclose(value, r_values, atol=1e-8, rtol=0) else 'no'}")
print(f"max_abs_diff {np.max(np.abs(value-r_values)):.17g}")
print(f"r_ms {r:.17g}")
print(f"translated_ms {ms:.17g}")
print(f"speedup {r/ms:.17g}")
