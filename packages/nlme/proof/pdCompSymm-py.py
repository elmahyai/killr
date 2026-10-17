import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nlme.pdcompsymm import pdCompSymm  # noqa: E402
from nlme.pdmat import is_initialized  # noqa: E402


def names_fp(names):
    names = list(names)
    out = [float(len(names))]
    for text in names:
        codes = [ord(ch) for ch in text]
        out.append(float(len(text)))
        out.append(float(sum(code * (index + 1) for index, code in enumerate(codes))))
    return out


def ncol_fp(value):
    return [-1.0] if value is None else [float(value)]


def build():
    matrix = np.full((3, 3), 0.6)
    np.fill_diagonal(matrix, 2.0)
    return {
        "p1": pdCompSymm([math.log(1.5), 0.4], nam=["a", "b", "c"]),
        "p2": pdCompSymm(matrix),
        "p3": pdCompSymm(nam=["x", "y", "z"]),
        "p4": pdCompSymm([0.1, -0.5], form="~ u + v - 1", data={"u": [1, 2, 3], "v": [2, 5, 1]}),
    }


def one():
    out = []
    for obj in build().values():
        out.append(float(is_initialized(obj)))
        out.extend(float(value) for value in obj.values)
        out.extend(ncol_fp(obj.ncol))
        out.extend(names_fp(obj.names))
    return np.asarray(out, dtype=np.float64)


def example():
    lines = []
    for name, obj in build().items():
        lines.append(f"{name} initialized: {int(is_initialized(obj))}")
        values = " ".join(f"{float(value):.10g}" for value in obj.values)
        lines.append(f"{name} values: {values}")
        ncol = "-1" if obj.ncol is None else str(obj.ncol)
        lines.append(f"{name} ncol: {ncol}")
        lines.append(f"{name} names: {' '.join(obj.names)}")
    return lines


out_dir = ROOT / "docs" / "output"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "pdCompSymm-python.txt").write_text("\n".join(example()) + "\n", encoding="utf-8")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (",".join("%.17g" % float(part) for part in value), statistics.median(elapsed))
)
