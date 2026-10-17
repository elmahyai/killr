import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nlme.pdblocked import pdBlocked  # noqa: E402
from nlme.pdcompsymm import pdCompSymm  # noqa: E402
from nlme.pddiag import pdDiag  # noqa: E402
from nlme.pdident import pdIdent  # noqa: E402
from nlme.pdlogchol import pdLogChol  # noqa: E402
from nlme.pdmatrix import pdMatrix  # noqa: E402


def build():
    return {
        "diag": pdDiag([0.1, -0.2, 0.3], nam=["a", "b", "c"]),
        "ident": pdIdent(0.3, nam=["a", "b", "c"]),
        "compsymm": pdCompSymm([np.log(1.5), 0.4], nam=["a", "b", "c"]),
        "logchol": pdLogChol([0.1, -0.2, 0.3, 0.4, 0.5, -0.1], nam=["a", "b", "c"]),
        "blocked": pdBlocked(
            [0.1, -0.2, 0.3, 0.4],
            nam=[["a", "b"], ["c", "d"]],
            pdClass=["pdDiag", "pdCompSymm"],
        ),
    }


def flat(matrix):
    return np.asarray(matrix, dtype=np.float64).ravel(order="F")


def one():
    objects = build()
    parts = []
    for key in ("diag", "ident", "compsymm", "logchol", "blocked"):
        parts.append(flat(pdMatrix(objects[key])))
        parts.append(flat(pdMatrix(objects[key], factor=True)))
    return np.concatenate(parts)


def example():
    lines = []
    for name, obj in build().items():
        matrix = pdMatrix(obj)
        factor = pdMatrix(obj, factor=True)
        lines.append(
            f"{name} matrix (column-major): "
            + " ".join(f"{value:.10g}" for value in flat(matrix))
        )
        lines.append(
            f"{name} factor (column-major): "
            + " ".join(f"{value:.10g}" for value in flat(factor))
        )
    return lines


out_dir = ROOT / "docs" / "output"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "pdMatrix-python.txt").write_text("\n".join(example()) + "\n", encoding="utf-8")

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
