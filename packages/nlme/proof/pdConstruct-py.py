import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nlme.pdcompsymm import pdCompSymm  # noqa: E402
from nlme.pdconstruct import pdConstruct  # noqa: E402
from nlme.pddiag import pdDiag  # noqa: E402
from nlme.pdident import pdIdent  # noqa: E402
from nlme.pdlogchol import pdLogChol  # noqa: E402
from nlme.pdmat import is_initialized  # noqa: E402

M3 = np.array([[4.0, 1.0, 0.5], [1.0, 3.0, 0.2], [0.5, 0.2, 2.0]])


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
    o1 = pdDiag(nam=["a", "b", "c"])
    o2 = pdCompSymm(nam=["a", "b", "c"])
    o3 = pdLogChol(nam=["x", "y", "z"])
    o4 = pdIdent(nam=["a", "b"])
    return {
        "r1": pdConstruct(o1, [0.1, 0.2, 0.3]),
        "r2": pdConstruct(o2, [0.2, 0.5]),
        "r3": pdConstruct(o3, M3),
        "r4": pdConstruct(o4, 0.25),
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
        lines.append(f"{name} class: {obj.pd_class}")
        values = " ".join(f"{float(value):.10g}" for value in obj.values)
        lines.append(f"{name} values: {values}")
        ncol = "-1" if obj.ncol is None else str(obj.ncol)
        lines.append(f"{name} ncol: {ncol}")
        lines.append(f"{name} names: {' '.join(obj.names)}")
    return lines


out_dir = ROOT / "docs" / "output"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "pdConstruct-python.txt").write_text("\n".join(example()) + "\n", encoding="utf-8")

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
