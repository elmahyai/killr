import statistics
import time

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from killplot import _phi, statefig  # noqa: E402

connect = np.array(
    [
        [0, 1, 2],
        [1, 0, 1],
        [0, 0, 0],
    ],
    dtype=float,
)
names = ["well", "ill", "dead"]


def fmt(x):
    flat = np.asarray(x, dtype=float).reshape(-1)
    parts = []
    for v in flat:
        if np.isnan(v):
            parts.append("NA")
        else:
            parts.append(f"{v:.17g}")
    return ",".join(parts)


def one():
    fig, ax = plt.subplots(figsize=(4, 4))
    a = statefig(ax, [2, 1], connect, names)
    fig2, ax2 = plt.subplots(figsize=(4, 4))
    b = statefig(ax2, [[1], [2]], connect, names, offset=0.02)
    fig3, ax3 = plt.subplots(figsize=(4, 4))
    cc = statefig(ax3, np.array([[0.1, 0.2], [0.5, 0.8], [0.9, 0.5]]), connect, names)
    p1 = _phi(0, 0, 1, 0, 0.3, (0.05, 0.05), (0.05, 0.05))
    p2 = _phi(0, 0, 1, 1, -0.4, (0.03, 0.04), (0.02, 0.05))
    p3 = _phi(0.2, 0.1, 0.8, 0.6, 0.25, (0.04, 0.03), (0.02, 0.06))
    out = [
        fmt(a),
        fmt(b),
        fmt(cc),
        fmt(np.concatenate([p1["center"], p1["angle"], [p1["r"]]])),
        fmt(np.concatenate([p2["center"], p2["angle"], [p2["r"]]])),
        fmt(np.concatenate([p3["center"], p3["angle"], [p3["r"]]])),
    ]
    for f in (fig, fig2, fig3):
        plt.close(f)
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
