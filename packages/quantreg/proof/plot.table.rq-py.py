"""Python side of the plot.table.rq proof.

plot.table.rq is the defunct table.rq message. It draws nothing, so the proof
compares the text printed for each case with the text R printed. The timed
call prints the same message as the R timed call.
"""

import contextlib
import io
import sys
from pathlib import Path

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF))

import numpy as np  # noqa: E402

from plot_proof_common import OUT, compare, read_r_cases, time_median_call_ms  # noqa: E402
from quantreg import rq, summary_rqs  # noqa: E402
from quantreg.plot import plot_table_rq  # noqa: E402

stem = "plot.table.rq"
A = np.loadtxt(PROOF.parent / "quantreg" / "data" / "check_design.txt")
X = A[:, :3]
y = A[:, 3]
data = {"y": y, "x1": X[:, 1], "x2": X[:, 2]}
fit = rq("y ~ x1 + x2", tau=[0.25, 0.5, 0.75], data=data)
summary = summary_rqs(fit, se="nid")


def text_of(x):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        plot_table_rq(x)
    return buffer.getvalue()


cases = {
    "rqs_fit": lambda: text_of(fit),
    "summary_list": lambda: text_of(summary),
}
out: list[str] = []
for name, run in cases.items():
    out.append(f"CASE {name}")
    out.append(run())
(OUT / f"{stem}-py.txt").write_text("\n".join(out) + "\n")

ms = time_median_call_ms(lambda: text_of(fit))

r_cases = read_r_cases(OUT / f"{stem}-r.txt")
py_cases = read_r_cases(OUT / f"{stem}-py.txt")
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
print(f"translated_ms {ms:.17g}")
print(f"speedup {r_ms / ms:.17g}")
