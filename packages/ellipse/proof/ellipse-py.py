import statistics
import time
from pathlib import Path

import numpy as np

from ellipse.ellipse import ellipse


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "output"
cases = [
    dict(x=0.35, scale=(2, 1.5), centre=(0.2, -0.4), level=0.90, npoints=17),
    dict(
        x=np.array([[4, 1.2], [1.2, 9]]),
        center=(-1.1, 2.3),
        level=0.95,
        which=(2, 1),
        npoints=33,
    ),
    dict(x=-0.8, scale=(0.7, 2.1), centre=(3, 0), t=1.7, npoints=64),
]


def run_all():
    return [ellipse(**case) for case in cases]


run_all()
elapsed = []
result = None
for _ in range(20):
    t0 = time.perf_counter()
    result = run_all()
    elapsed.append(time.perf_counter() - t0)

max_diff = 0.0
for i, values in enumerate(result, 1):
    np.savetxt(OUTPUT / f"ellipse-python-case{i}.txt", values, fmt="%.17g")
    reference = np.loadtxt(OUTPUT / f"ellipse-r-case{i}.txt")
    max_diff = max(max_diff, float(np.max(np.abs(values - reference))))

r_ms = float((OUTPUT / "ellipse-r.txt").read_text().split()[1])
python_ms = statistics.median(elapsed) * 1000
speedup = r_ms / python_ms
(OUTPUT / "ellipse-python.txt").write_text(
    f"python_ms {python_ms:.17g}\n"
    f"max_abs_diff {max_diff:.17g}\n"
    f"speedup {speedup:.17g}\n"
)
print(f"matched {'yes' if max_diff <= 1e-8 else 'no'}")
print(f"max_abs_diff {max_diff:.17g}")
print(f"r_ms {r_ms:.17g}")
print(f"python_ms {python_ms:.17g}")
print(f"speedup {speedup:.17g}")
