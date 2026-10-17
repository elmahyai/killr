import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.varcorr import Lme, ModelStruct, PdMat, ReStruct, VarCorr

_CORR = np.array(
    [[1.0, -0.6093329], [-0.6093329, 1.0]],
    dtype=np.float64,
)


def _orthodont_fm1() -> Lme:
    pd = PdMat(
        corr=_CORR,
        std_dev=(1.7763081210416838, 0.17284040710511267),
        std_dev_names=("(Intercept)", "age"),
        formula="~age",
        pd_class="pdLogChol",
    )
    return Lme(
        modelStruct=ModelStruct(ReStruct((("Subject", pd),))),
        sigma=1.3100396928196838,
    )


def one():
    vc = VarCorr(_orthodont_fm1())
    flat = np.ravel(vc.values, order="F")
    out = np.empty(flat.size, dtype=np.float64)
    for index, cell in enumerate(flat):
        try:
            out[index] = float(cell)
        except (TypeError, ValueError):
            out[index] = np.nan
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (",".join("null" if np.isnan(part) else "%.17g" % float(part) for part in value), statistics.median(elapsed))
)
