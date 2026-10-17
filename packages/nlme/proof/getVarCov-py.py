import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.getvarcov import Lme, ModelStruct, ReStructBlock, getVarCov

# Random-effects variance matrix from the getVarCov help-page lme fit (Female Orthodont).
_SIGMA = 0.66827462637435753
_RESTRUCT = np.array(
    [
        [7.9494496947945654, -0.24068628957961252],
        [-0.24068628957961252, 0.057989820909800073],
    ],
    dtype=np.float64,
)


def _fm1_stand_in() -> Lme:
    return Lme(
        sigma=_SIGMA,
        modelStruct=ModelStruct(reStruct=(ReStructBlock(_RESTRUCT),)),
        groups=((),),
        group_names=("Subject",),
    )


def one():
    result = getVarCov(_fm1_stand_in())
    return np.ravel(np.asarray(result, dtype=np.float64), order="F")


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
