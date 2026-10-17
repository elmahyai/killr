"""Python side of the plot.summary.rqss proof.

R's plot.summary.rqss has no plot: it raises a warning and draws nothing. The
Python version warns with the same text. The check is the warning text, compared
exactly with the R output. The timed call is the warning itself, with the warning
caught in the same way on both sides.
"""

import sys
import warnings
from pathlib import Path

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF))

import numpy as np  # noqa: E402

from plot_proof_common import OUT, time_median_call_ms  # noqa: E402
from quantreg.rqss import rqss  # noqa: E402
from quantreg.rqss_methods import summary_rqss  # noqa: E402
from quantreg.rqss_plot import plot_summary_rqss  # noqa: E402

stem = "plot.summary.rqss"
n = 60
i = np.arange(1, n + 1, dtype=float)
x = 2 * np.sin(i)
z = np.cos(0.7 * i)
y = np.sin(x) + 0.5 * z + 0.3 * np.sin(7 * i)
data = {"y": y, "x": x, "z": z}
f2 = rqss("y ~ qss(x, lambda=2) + qss(z, lambda=1, Dorder=0)", data, tau=0.5)
s = summary_rqss(f2)


def warn_text():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        plot_summary_rqss(s)
    return str(caught[0].message)


message = warn_text()
(OUT / f"{stem}-python.txt").write_text(message + "\n")

ms = time_median_call_ms(warn_text)

r_text = (OUT / f"{stem}-r.txt").read_text()
py_text = (OUT / f"{stem}-python.txt").read_text()
same = r_text == py_text
print(f"matches {'yes' if same else 'no'}")
print(f"text {py_text.strip()!r}")
r_ms = float((OUT / f"{stem}-r-time.txt").read_text())
print(f"r_ms {r_ms:.17g}")
print(f"translated_ms {ms:.17g}")
print(f"speedup {r_ms / ms:.17g}")
