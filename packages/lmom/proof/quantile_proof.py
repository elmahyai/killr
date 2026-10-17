"""Compare all requested lmom quantiles with R lmom 3.3."""

from __future__ import annotations

import statistics
import time
from pathlib import Path

import numpy as np

from lmom.quaexp import quaexp
from lmom.quagam import quagam
from lmom.quagev import quagev
from lmom.quaglo import quaglo
from lmom.quagno import quagno
from lmom.quagpa import quagpa
from lmom.quagum import quagum
from lmom.quakap import quakap
from lmom.qualn3 import qualn3
from lmom.quanor import quanor
from lmom.quape3 import quape3
from lmom.quawak import quawak
from lmom.quawei import quawei

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "docs" / "output"
F = np.array([0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99])
CASES = {
    "quaexp": (quaexp, (1.2, 2.3)),
    "quagam": (quagam, (2.4, 1.7)),
    "quagev": (quagev, (1.2, 2.3, 0.25)),
    "quaglo": (quaglo, (1.2, 2.3, -0.25)),
    "quagno": (quagno, (1.2, 2.3, 0.25)),
    "quagpa": (quagpa, (1.2, 2.3, -0.25)),
    "quagum": (quagum, (1.2, 2.3)),
    "quakap": (quakap, (1.2, 2.3, 0.25, -0.15)),
    "qualn3": (qualn3, (1.2, 0.3, 0.8)),
    "quanor": (quanor, (1.2, 2.3)),
    "quape3": (quape3, (1.2, 2.3, -0.8)),
    "quawak": (quawak, (1.2, 2.3, 0.25, 0.8, -0.15)),
    "quawei": (quawei, (1.2, 2.3, 1.7)),
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    r_values = {}
    for line in (OUT / "quantile_r_values.txt").read_text().splitlines():
        name, *values = line.split()
        r_values[name] = np.array([float(value) for value in values])
    r_times = {
        name: float(seconds)
        for name, seconds in (line.split() for line in (OUT / "quantile_r_timings.txt").read_text().splitlines())
    }
    rows = []
    py_lines = []
    for name, (fun, para) in CASES.items():
        values = np.asarray(fun(F, para), dtype=float)
        py_lines.append(" ".join([name, *[f"{value:.17g}" for value in values]]))
        fn = lambda: fun(F, para)
        fn()
        times = []
        for _ in range(20):
            start = time.perf_counter(); fn(); times.append(time.perf_counter() - start)
        py_ms = statistics.median(times) * 1000
        diff = float(np.max(np.abs(values - r_values[name])))
        r_ms = r_times[name] * 1000
        rows.append((name, diff, r_ms, py_ms, r_ms / py_ms))
    (OUT / "quantile_python_values.txt").write_text("\n".join(py_lines) + "\n")
    lines = ["function matches max_abs_diff r_ms translated_ms speedup"]
    for name, diff, r_ms, py_ms, speedup in rows:
        lines.append(f"{name} {'yes' if diff <= 1e-8 else 'no'} {diff:.3e} {r_ms:.6f} {py_ms:.6f} {speedup:.6f}")
    (OUT / "quantile_proof.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if all(diff <= 1e-8 for _, diff, *_ in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
