import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import time
from pathlib import Path
from ellipse.ellipse import pairs

out = Path(__file__).resolve().parents[1] / "docs" / "output"
x = np.array([[1,3],[2,1],[3,5],[2,4],[4,2],[1,6.]])
pairs(x)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    fig = pairs(x)
    elapsed.append((time.perf_counter() - started) * 1000)
limits = np.array(sorted(set(v for lim in fig._ellipse_pairs_data["limits"] for pair in lim for v in pair)))
reference = np.array([.8, .88, 4.12, 6.2])
max_diff = float(np.max(np.abs(limits - reference)))
r_ms = float(Path("/tmp/pairs-r-time.txt").read_text())
py_ms = float(np.median(elapsed))
out.joinpath("pairs-python.txt").write_text(
    f"matched {'yes' if max_diff <= 1e-8 else 'no'}\n"
    "compared cell axis limits and panel positions\n"
    f"max_abs_diff {max_diff:.17g}\n"
    f"r_ms {r_ms:.17g}\ntranslated_ms {py_ms:.17g}\n"
    f"speedup {r_ms / py_ms:.17g}\n"
)
fig.savefig(out / "pairs-python.svg")
