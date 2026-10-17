import statistics
import sys
import time
from pathlib import Path

import types

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if "nlme" not in sys.modules:
    _pkg = types.ModuleType("nlme")
    _pkg.__path__ = [str(ROOT / "nlme")]
    sys.modules["nlme"] = _pkg

from nlme.initialize import Initialize
from nlme.var_ident import _NlmeFrame
from nlme.var_power import coef, var_weights, varPower


def one():
    data = _NlmeFrame(
        {
            "y": np.arange(1, 7, dtype=np.float64),
            "x": np.array([1.2, 2.5, 3.1, 4.0, 5.5, 6.3], dtype=np.float64),
            "grp": np.array(["A", "A", "B", "B", "A", "B"], dtype=object),
        }
    )
    vf1 = Initialize(varPower(0.35, form="~x"), data)
    vf2 = Initialize(varPower(value={"A": 0.3, "B": 0.6}, form="~x|grp"), data)
    return np.concatenate(
        [
            np.ravel(coef(vf1, unconstrained=True, allCoef=False).values),
            np.ravel(coef(vf1, unconstrained=True, allCoef=True).values),
            np.ravel(var_weights(vf1)),
            np.asarray([vf1.log_lik], dtype=np.float64),
            np.ravel(coef(vf2, unconstrained=True, allCoef=False).values),
            np.ravel(coef(vf2, unconstrained=True, allCoef=True).values),
            np.ravel(var_weights(vf2)),
            np.asarray([vf2.log_lik], dtype=np.float64),
        ]
    ).astype(np.float64)


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
