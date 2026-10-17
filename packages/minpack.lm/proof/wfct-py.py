import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from minpacklm.wfct import puromycin_treated, wfct_eval

FORMULA = "rate ~ Vm * conc/(K + conc)"
START = {"Vm": 200.0, "K": 0.05}


def one():
    treated = puromycin_treated()
    return np.concatenate(
        [
            wfct_eval("1/rate", formula=FORMULA, data=treated, start=START),
            wfct_eval("sqrt(conc)", formula=FORMULA, data=treated, start=START),
            wfct_eval("1/fitted**2", formula=FORMULA, data=treated, start=START),
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
    % (
        ",".join("%.17g" % float(part) for part in value),
        statistics.median(elapsed),
    )
)
