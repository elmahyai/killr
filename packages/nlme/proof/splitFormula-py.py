import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
_py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
_site = ROOT / ".venv" / "lib" / _py_ver / "site-packages"
sys.path[:0] = [
    str(ROOT / "packages" / "nlme"),
    str(_site),
    str(ROOT / "crates" / "onecomp"),
]
from nlme.splitformula import proof_values, splitFormula


def one():
    cases = [
        ("~a/b/c", None),
        ("y ~ (a + b) / c", None),
        ("~x * z / w", None),
        ("~a + b/c", None),
        ("~a:b/c", None),
        ("~p/q", "/"),
    ]
    out = []
    for text, sep in cases:
        pieces = splitFormula(text) if sep is None else splitFormula(text, sep=sep)
        out.extend(proof_values(pieces))
    return np.asarray(out, dtype=np.float64)


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
