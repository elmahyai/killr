import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.asoneformula import _all_vars
from nlme.getcovariateformula import getCovariateFormula
from nlme.var_power import varPower
from nlme.varfunc import varFunc


def one():
    vp = varPower(0.35, form="~x")
    try:
        varFunc(1.0)
        err = 0.0
    except ValueError:
        err = 1.0
    fixed = varFunc("~x")
    return np.asarray(
        [
            1.0 if varFunc(None) is None else 0.0,
            1.0 if varFunc(vp) is vp else 0.0,
            1.0 if fixed.classes == ("varFixed", "varFunc") else 0.0,
            1.0 if varFunc("~x").classes == ("varFixed", "varFunc") else 0.0,
            float(len(_all_vars(getCovariateFormula(fixed.formula).text))),
            err,
        ],
        dtype=np.float64,
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
