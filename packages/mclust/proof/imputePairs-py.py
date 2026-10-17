import statistics
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "packages" / "mclust"))
sys.path.insert(0, str(ROOT / "killplot"))

from mclust.impute_pairs import _points, _text_label, impute_pairs  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "output"

out = []


def emit(*parts):
    out.append(" ".join(str(p) for p in parts))


def num(values):
    arr = np.atleast_1d(np.asarray(values, dtype=float))
    return " ".join("%.17g" % v for v in arr)


def usr(ax):
    return list(ax.get_xlim()) + list(ax.get_ylim())


def rec_panel(tag):
    def panel(ax, x, y, pch, col):
        emit("panel", tag, "usr", num(usr(ax)), "pch", num(pch),
             "col", " ".join(col), "x", num(x), "y", num(y))
        _points(ax, x, y, pch, col)

    return panel


def rec_text(ax, x, y, txt, cex, font):
    emit("label", num(x), num(y), txt, "usr", num(usr(ax)),
         "cex", num(cex), "font", num(font))
    _text_label(ax, x, y, txt, cex, font)


def make_data():
    t = np.arange(1, 13, dtype=float)
    x = np.column_stack([t / 4 + np.sin(t), np.cos(t * 0.7) * 3, (t**2 % 7) / 2])
    for r, c in [(1, 0), (4, 1), (8, 2), (10, 0)]:
        x[r, c] = np.nan
    return x


def impute_mean(x):
    y = x.copy()
    m = np.nanmean(x, axis=0)
    for j in range(x.shape[1]):
        y[np.isnan(y[:, j]), j] = m[j]
    return y


def run_case(extra):
    global out
    out = []
    d = make_data()
    di = impute_mean(d)
    fig = plt.figure(figsize=(7.0, 7.0))
    kwargs = dict(
        lower_panel=rec_panel("lower"),
        upper_panel=rec_panel("upper"),
        text_panel=rec_text,
        cex_labels=1,
        fig=fig,
    )
    kwargs.update(extra)
    impute_pairs(d, di, **kwargs)
    fig.canvas.draw()
    plt.close(fig)
    return list(out)


def one():
    lines = []
    lines.append("case A row1attop TRUE")
    lines += run_case(dict(labels=["alpha", "beta", "gamma"], row1attop=True))
    lines.append("case B row1attop FALSE")
    lines += run_case(dict(labels=["alpha", "beta", "gamma"], row1attop=False))
    lines.append("case C labels NULL")
    lines += run_case(dict(labels=None))
    lines.append("case D labels missing")
    lines += run_case(dict())
    return lines


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for line in value:
    print(line)
print("MS %.17g" % statistics.median(elapsed))

# Figure for the example: the same data with the default cex.labels.
d = make_data()
fig = plt.figure(figsize=(7.0, 7.0))
impute_pairs(d, impute_mean(d), labels=["alpha", "beta", "gamma"], fig=fig)
OUT_DIR.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT_DIR / "imputePairs-py.svg", format="svg")
plt.close(fig)
