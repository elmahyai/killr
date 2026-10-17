import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.var_ident import _NlmeFrame, initialize as initialize_var_ident, varIdent
from nlme.var_power import initialize as initialize_var_power, varPower
from nlme.varcomb import varComb
from nlme.varweights import varWeights


def one():
    data = _NlmeFrame(
        {
            "y": np.arange(1, 10, dtype=np.float64),
            "x": np.array([1.2, 2.5, 3.1, 4.0, 5.5, 6.3, 2.2, 3.3, 4.4], dtype=np.float64),
            "grp": np.array(["A", "A", "B", "B", "C", "C", "A", "B", "C"], dtype=object),
        }
    )
    vp = initialize_var_power(varPower(0.35, form="~x"), data)
    vi = initialize_var_ident(varIdent(value={"B": 2.0, "C": 3.0}, form="~1 | grp"), data)
    vc = varComb(vp, vi)
    return np.concatenate(
        [
            np.asarray(varWeights(vp), dtype=np.float64).reshape(-1),
            np.asarray(varWeights(vc), dtype=np.float64).reshape(-1),
        ]
    )


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
