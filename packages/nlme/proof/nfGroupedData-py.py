import statistics
import sys
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if "nlme" not in sys.modules:
    _pkg = types.ModuleType("nlme")
    _pkg.__path__ = [str(ROOT / "nlme")]
    sys.modules["nlme"] = _pkg

from nlme.nfgroupeddata import nfGroupedData


def one():
    frame = {
        "y": [1, 2, 3, 4, 5, 7],
        "x": [1, 2, 1, 2, 1, 2],
        "g": ["b", "b", "a", "a", "c", "c"],
    }
    out = nfGroupedData("y ~ x | g", data=frame)
    return [
        *(out.columns["g"].codes + 1).astype(float),
        *out.columns["y"],
        *out.columns["x"],
        float("nfGroupedData" in out.classes),
        float("nfnGroupedData" in out.classes),
        float(out.attributes["order.groups"]),
    ]


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
