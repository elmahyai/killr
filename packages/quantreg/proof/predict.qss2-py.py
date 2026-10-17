"""Python side of the predict.qss2 proof.

Runs quantreg.rqss_methods.predict_qss2 on the cases that predict.qss2-r.R runs,
and writes the same text layout. The two outputs are compared token by token: text
must be equal and numbers must agree within 1e-8. The timed call is the grid case,
one untimed call first, then the median of 20 calls.
"""

import statistics
import sys
import time
from pathlib import Path

import numpy as np

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF))
ROOT = PROOF.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "interp"))

from plot_proof_common import OUT, compare, read_r_cases  # noqa: E402
from quantreg.rqss_methods import predict_qss2  # noqa: E402

stem = "predict.qss2"

d = np.loadtxt(ROOT / "quantreg" / "data" / "check_design.txt")
X = np.column_stack([d[:, 1], d[:, 2]])
px = X[:, 0]
py = X[:, 1]
pz = np.sin(2 * px) + py**2 - 0.5 * px * py
obj = np.column_stack([px, py, pz])

g = np.linspace(-0.6, 0.6, 9)
grid = np.column_stack([np.tile(g, 9), np.repeat(g, 9)])
idx = np.arange(0, 81, 8)
frame = {"x": grid[idx, 0] + 0.05, "y": grid[idx, 1] - 0.03}
bad_frame = {"a": frame["x"], "b": frame["y"]}
outside = np.array([[2.0, 2.0], [0.1, -0.2]])
three_cols = np.column_stack([grid[:, 0], grid[:, 1], np.ones(81)])
midpoints = (X[9:20] + X[10:21]) / 2

cases = {
    "matrix_grid": grid,
    "list_frame": frame,
    "pair_midpoints": midpoints,
    "names_conflict": bad_frame,
    "outside_hull": outside,
    "three_columns": three_cols,
}


def fmt(values):
    return " ".join("%.17g" % float(v) for v in np.asarray(values, dtype=float).ravel())


def case_lines(name, newdata):
    lines = [f"CASE {name}"]
    try:
        res = predict_qss2(obj, newdata)
    except ValueError as err:
        lines.append(f"ERR {err}")
        return lines
    x = np.asarray(res["x"], dtype=float)
    y = np.asarray(res["y"], dtype=float)
    z = np.asarray(res["z"], dtype=float)
    D = res["D"].toarray()
    lines.append(f"x {x.size} {fmt(x)}")
    lines.append(f"y {y.size} {fmt(y)}")
    lines.append(f"z {z.size} {fmt(z)}")
    lines.append(f"D {D.shape[0]} {D.shape[1]} {fmt(D)}")
    return lines


out: list[str] = []
for name, newdata in cases.items():
    out.extend(case_lines(name, newdata))
(OUT / f"{stem}-python.txt").write_text("\n".join(out) + "\n")

predict_qss2(obj, grid)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    predict_qss2(obj, grid)
    elapsed.append((time.perf_counter() - started) * 1000)
translated_ms = statistics.median(elapsed)

r_cases = read_r_cases(OUT / f"{stem}-r.txt")
py_cases = read_r_cases(OUT / f"{stem}-python.txt")
overall = True
worst = 0.0
for name in cases:
    ok, diff, count, msg = compare(r_cases[name], py_cases[name])
    overall = overall and ok
    worst = max(worst, diff)
    print(
        f"case {name}: matches {'yes' if ok else 'no'} numbers {count} "
        f"max_abs_diff {diff:.3g}" + ("" if ok else f" first_mismatch {msg}")
    )

r_ms = float((OUT / f"{stem}-r-time.txt").read_text())
print(f"matches {'yes' if overall else 'no'}")
print(f"max_abs_diff {worst:.17g}")
print(f"r_ms {r_ms:.17g}")
print(f"translated_ms {translated_ms:.17g}")
print(f"speedup {r_ms / translated_ms:.17g}")
