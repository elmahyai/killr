import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nlme.pdlogchol import pdLogChol  # noqa: E402
from nlme.pdmat import is_initialized  # noqa: E402


def names_fp(names):
    names = list(names)
    out = [float(len(names))]
    for text in names:
        codes = [ord(ch) for ch in text]
        out.append(float(len(text)))
        out.append(float(sum(code * (index + 1) for index, code in enumerate(codes))))
    return out


def build():
    matrix = np.array([[4.0, 1.0, 0.5], [1.0, 3.0, 0.2], [0.5, 0.2, 2.0]])
    return {
        "p1": pdLogChol([0.1, -0.2, 0.3, 0.4, 0.5, -0.1], nam=["a", "b", "c"]),
        "p2": pdLogChol(matrix),
        "p3": pdLogChol(nam=["x", "y"]),
        "p4": pdLogChol([0.2, -0.3, 0.1], form="~ u + v - 1", data={"u": [1, 2, 3], "v": [2, 5, 1]}),
    }


def one():
    out = []
    for obj in build().values():
        out.append(float(is_initialized(obj)))
        out.extend(float(value) for value in obj.values)
        out.extend(names_fp(obj.names))
    return np.asarray(out, dtype=np.float64)


def example():
    lines = []
    for name, obj in build().items():
        lines.append(f"{name} initialized: {int(is_initialized(obj))}")
        values = " ".join(f"{float(value):.10g}" for value in obj.values)
        lines.append(f"{name} values: {values}")
        lines.append(f"{name} names: {' '.join(obj.names)}")
    return lines


out_dir = ROOT / "docs" / "output"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "pdLogChol-python.txt").write_text("\n".join(example()) + "\n", encoding="utf-8")

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
