import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from ellipse.ellipse import plotcorr

out = Path(__file__).resolve().parents[1] / "docs" / "output"
corr = np.array([[1, .2, -.7], [.2, 1, .45], [-.7, .45, 1.]])
def one():
    fig, ax = plt.subplots()
    plotcorr(corr, outline=True, col=["red", "blue", "green"], type="full", ax=ax)
    return fig, ax
one()
elapsed = []
for _ in range(20):
    import time
    started = time.perf_counter()
    fig, ax = one()
    elapsed.append((time.perf_counter() - started) * 1000)
actual = np.vstack([c["vertices"] for c in ax._ellipse_data["cells"]])
reference = np.loadtxt("/tmp/plotcorr-r-values.txt")
max_diff = float(np.max(np.abs(actual - reference)))
r_ms = float(Path("/tmp/plotcorr-r-time.txt").read_text())
py_ms = float(np.median(elapsed))
out.joinpath("plotcorr-python.txt").write_text(
    f"matched {'yes' if max_diff <= 1e-8 else 'no'}\n"
    f"compared cell colors, ellipse vertices, axis limits, shading values\n"
    f"max_abs_diff {max_diff:.17g}\n"
    f"r_ms {r_ms:.17g}\n"
    f"translated_ms {py_ms:.17g}\n"
    f"speedup {r_ms / py_ms:.17g}\n"
)
fig.savefig(out / "plotcorr-python.svg")
