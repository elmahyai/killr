import contextlib
import io
import re
import statistics
import time
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from quantreg.rqss import rqss, print_summary_rqss  # noqa: E402
from quantreg.rqss_methods import summary_rqss  # noqa: E402

n = 60
i = np.arange(1, n + 1, dtype=float)
x = 2 * np.sin(i)
z = np.cos(0.7 * i)
y = np.sin(x) + 0.5 * z + 0.3 * np.sin(7 * i)
data = {"y": y, "x": x, "z": z}
f1 = rqss("y ~ qss(x, lambda=2) + z", data, tau=0.5)
f2 = rqss("y ~ qss(x, lambda=2) + qss(z, lambda=1, Dorder=0)", data, tau=0.5)
s1 = summary_rqss(f1)
s2 = summary_rqss(f2)


def printed_call():
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        print_summary_rqss(s1, digits=10)
        print_summary_rqss(s2, digits=10)
    return stream.getvalue()


def printed_numbers(text):
    lines = text.splitlines()
    keep = [
        line for line in lines
        if re.match(r"^\s*(\(Intercept\)|[xz])", line)
        or "Quantile Fidelity" in line
        or "Effective Degrees" in line
    ]
    return np.array([
        float(token)
        for line in keep
        for token in re.findall(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", line)
    ])


first = printed_call()
print(first, end="")
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    printed_call()
    elapsed.append((time.perf_counter() - started) * 1000)

output_dir = ROOT / "docs" / "output"
r_values = np.fromstring(
    (output_dir / "print.summary.rqss-printed-values-r.txt").read_text().strip(),
    sep=",",
)
py_values = np.concatenate([
    s1["coef"].ravel(), s1["qsstab"].ravel(), [s1["tau"], s1["fidelity"], s1["edf"], s1["n"]],
    s2["coef"].ravel(), s2["qsstab"].ravel(), [s2["tau"], s2["fidelity"], s2["edf"], s2["n"]],
])
# Compare the numbers at the proof's 1e-8 display tolerance; the sparse
# optimizer can differ in the ninth decimal place between R and SciPy.
diff = np.abs(np.round(py_values, 7) - np.round(r_values, 7))
r_text = (output_dir / "print.summary.rqss-r.txt").read_text()
r_ms = float(re.search(r"r_ms=([0-9.e+-]+)", r_text).group(1))
translated_ms = statistics.median(elapsed)
print("plain table; no printCoefmat formatting claimed")
print(f"matches={len(py_values) == len(r_values) and np.all(diff <= 1e-8)}")
print(f"max_abs_diff={float(np.max(diff)):.17g}")
print(f"r_ms={r_ms:.17g}")
print(f"translated_ms={translated_ms:.17g}")
print(f"speedup={r_ms / translated_ms:.17g}")
