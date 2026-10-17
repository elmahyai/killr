import statistics
import sys
import time
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
# Load the nlme modules without running nlme/__init__.py, which imports the
# onecomp extension (phenoModel) that is not built in this environment.
if "nlme" not in sys.modules:
    _pkg = types.ModuleType("nlme")
    _pkg.__path__ = [str(ROOT / "nlme")]
    sys.modules["nlme"] = _pkg

from nlme.corident import CorIdent, corIdent  # noqa: E402
from nlme.corcompsymm import corCompSymm, initialize as initialize_comp  # noqa: E402
from nlme.corlin import corLin, initialize as initialize_lin  # noqa: E402
from nlme.corratio import corRatio, initialize as initialize_ratio  # noqa: E402
from nlme.corspher import corSpher, initialize as initialize_spher  # noqa: E402
from nlme.corsymm import corSymm, initialize as initialize_symm  # noqa: E402
from nlme.logdet import logDet  # noqa: E402
from nlme.matrix_assign import matrix_assign  # noqa: E402
from nlme.pdmat import pdMat  # noqa: E402
from nlme.restruct import load_pixel_csv, reStruct  # noqa: E402


def one():
    mat = np.array([[2.0, 0.5], [0.5, 1.0]])
    s = matrix_assign(pdMat(nam=("a", "b"), pdClass="pdSymm"), mat)
    lc = matrix_assign(pdMat(nam=("a", "b"), pdClass="pdLogChol"), mat)
    d = matrix_assign(pdMat(nam=("a", "b"), pdClass="pdDiag"), np.diag([2.0, 3.0]))
    i = matrix_assign(pdMat(nam=("a", "b"), pdClass="pdIdent"), 2.0 * np.eye(2))
    cs = matrix_assign(
        pdMat(nam=("a", "b"), pdClass="pdCompSymm"),
        np.array([[2.0, 0.6], [0.6, 2.0]]),
    )
    rs1 = reStruct({"Dog": "~day", "Side": "~1"}, data=load_pixel_csv())
    rs1 = matrix_assign(rs1, [np.diag([4.0, 2.0]), np.array([[3.0]])])
    ident = corIdent()
    assert isinstance(ident, CorIdent)
    values = [
        logDet(s),
        logDet(lc),
        logDet(d),
        logDet(i),
        logDet(cs),
        *logDet(rs1),
        logDet(ident),
        logDet(initialize_comp(corCompSymm(0.2, form="~ 1 | g"), {"g": [1, 1, 1]})),
        logDet(initialize_symm(corSymm([0.0, 0.0, 0.0], form="~ 1 | g"), {"g": [1, 1, 1]})),
        logDet(initialize_lin(corLin(2.5, form="~ x + y"), {"x": [0, 1, 0.5, 2], "y": [0, 0, 1, 0.5]})),
        logDet(initialize_ratio(corRatio(1.8, form="~ x + y"), {"x": [0, 1, 0.5, 2], "y": [0, 0, 1, 0.5]})),
        logDet(initialize_spher(corSpher(2.5, form="~ x + y"), {"x": [0, 1, 0.5, 2], "y": [0, 0, 1, 0.5]})),
    ]
    return np.asarray(values, dtype=np.float64)


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
