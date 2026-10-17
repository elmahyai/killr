import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.var_ident import _NlmeFrame, initialize, proof_values, varIdent


def one():
    data = _NlmeFrame(
        {
            "y": np.arange(1, 10, dtype=np.float64),
            "grp": np.array(["A", "A", "B", "B", "C", "C", "A", "B", "C"], dtype=object),
        }
    )
    vf = varIdent(value={"B": 2.0, "C": 3.0}, form="~1 | grp")
    vf = initialize(vf, data)
    return proof_values(vf)


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
