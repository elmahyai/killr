import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nlme.pdblocked import pdBlocked  # noqa: E402
from nlme.pdmat import is_initialized  # noqa: E402


def names_fp(names):
    names = list(names)
    out = [float(len(names))]
    for text in names:
        codes = [ord(ch) for ch in text]
        out.append(float(len(text)))
        out.append(float(sum(code * (index + 1) for index, code in enumerate(codes))))
    return out


def blocked_initialized(obj):
    return all(is_initialized(block) for block in obj.blocks)


def coef_values(obj):
    return [float(v) for block in obj.blocks for v in np.asarray(block.values).ravel()]


def build():
    return {
        "b1": pdBlocked(
            [0.1, -0.2, 0.3, 0.4],
            nam=[["a", "b"], ["c", "d"]],
            pdClass=["pdDiag", "pdCompSymm"],
        ),
        "b2": pdBlocked(nam=[["a", "b"], ["c", "d"]], pdClass=["pdDiag", "pdCompSymm"]),
        "b3": pdBlocked(
            [0.1, 0.2, 0.3, 0.4, 0.5, -0.1, 0.7, 0.2],
            nam=[["a", "b", "c"], ["d", "e"]],
            pdClass=["pdLogChol", "pdDiag"],
        ),
        "b4": pdBlocked([0.5, 0.1], nam=[["a", "b"], ["c"]], pdClass=["pdIdent", "pdDiag"]),
    }


def one():
    out = []
    for obj in build().values():
        out.append(float(blocked_initialized(obj)))
        out.extend(coef_values(obj))
        out.extend(names_fp(obj.dimnames[1] if obj.dimnames else ()))
        out.extend(float(len(names)) for names in obj.names_list)
    return np.asarray(out, dtype=np.float64)


def example():
    lines = []
    for name, obj in build().items():
        lines.append(f"{name} initialized: {int(blocked_initialized(obj))}")
        lines.append(
            f"{name} coef: " + " ".join(f"{value:.10g}" for value in coef_values(obj))
        )
        lines.append(f"{name} names: {' '.join(obj.dimnames[1]) if obj.dimnames else ''}")
        lines.append(
            f"{name} block sizes: " + " ".join(str(len(names)) for names in obj.names_list)
        )
    return lines


out_dir = ROOT / "docs" / "output"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "pdBlocked-python.txt").write_text("\n".join(example()) + "\n", encoding="utf-8")

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
