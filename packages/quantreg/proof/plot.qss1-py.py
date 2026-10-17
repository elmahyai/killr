import statistics
import time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from quantreg.plot import plot_qss1

xyz = np.column_stack(([0, 1, 2, 4], [2, 3, 1, 5]))

def one():
    fig = plt.figure()
    plot_qss1(xyz, rug=False, fig=fig)
    plt.close(fig)
    return np.concatenate([xyz[:, 0], xyz[:, 1]])

one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value = one()
fig = plt.figure()
plot_qss1(xyz, rug=False, fig=fig)
fig.savefig("packages/quantreg/docs/output/plot.qss1-python.svg")
plt.close(fig)
print(",".join(f"{item:.17g}" for item in value))
print(f"{statistics.median(elapsed):.17g}")
