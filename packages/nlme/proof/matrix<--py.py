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

from nlme.matrix_assign import matrix_assign  # noqa: E402
from nlme.pdmat import pdMat  # noqa: E402
from nlme.restruct import load_pixel_csv, reStruct  # noqa: E402


def one():
    mat = np.array([[2.0, 0.5], [0.5, 1.0]])
    p = matrix_assign(pdMat(nam=("a", "b"), pdClass="pdSymm"), mat)
    q = matrix_assign(pdMat(nam=("a", "b"), pdClass="pdLogChol"), mat)
    rs1 = reStruct({"Dog": "~day", "Side": "~1"}, data=load_pixel_csv())
    rs1 = matrix_assign(rs1, [np.diag([4.0, 2.0]), np.array([[3.0]])])
    side, dog = rs1.blocks[0][1], rs1.blocks[1][1]
    values = [
        *p.values,
        *q.values,
        float(len(p.values)),
        1.0,
        *side.values,
        *dog.values,
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
