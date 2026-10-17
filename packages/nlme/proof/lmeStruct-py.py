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

from nlme.corar1 import CorAR1, corAR1  # noqa: E402
from nlme.isinitialized import isInitialized  # noqa: E402
from nlme.lmestruct import lmeStruct  # noqa: E402
from nlme.restruct import load_pixel_csv, reStruct  # noqa: E402


def one():
    pixel = load_pixel_csv()
    rs1 = reStruct({"Dog": "~day", "Side": "~1"}, data=pixel)
    ls1 = lmeStruct(rs1)
    ls2 = lmeStruct(rs1, corStruct=corAR1(0.5))
    values = [
        *[float(part) for part in ls1.settings],
        float(len(ls1)),
        float(ls1.classes.count("lmeStruct") > 0),
        float("modelStruct" in ls1.classes),
        float(ls1.names == ["reStruct"]),
        float(len(ls2)),
        float("reStruct" in ls2.names),
        float("corStruct" in ls2.names),
        float(ls2.varStruct is None),
        float(isInitialized(ls2.reStruct)),
        *[float(part) for part in ls2.settings],
        float(len(ls2.reStruct)),
        float(isinstance(ls2.corStruct, CorAR1)),
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
