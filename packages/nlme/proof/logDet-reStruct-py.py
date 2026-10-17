import json
import statistics
import sys
import time
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Load the nlme modules without running nlme/__init__.py (it imports phenoModel).
if "nlme" not in sys.modules:
    _pkg = types.ModuleType("nlme")
    _pkg.__path__ = [str(ROOT / "nlme")]
    sys.modules["nlme"] = _pkg
from nlme.restruct import load_pixel_csv, reStruct
from nlme.initialize import Initialize
from nlme.logdet import logDet
from nlme.matrix_assign import pd_matrix_from_params
from nlme.restruct import coef
from nlme.glsapvar import ConLin

# Fixed input: the conLin lme() passes to Initialize.reStruct on the Pixel example
# (written by proof/reStruct-conlin-capture-r.R).
_FIXTURE = json.loads((ROOT / "proof" / "data" / "reStruct-pixel-conlin.json").read_text())
N = int(_FIXTURE["N"])
NCOL = int(_FIXTURE["ncol"])
CONLIN_XY = np.asarray(_FIXTURE["Xy"], dtype=np.float64).reshape(N, NCOL, order="F")
CONLIN_DIMS = _FIXTURE["dims"]
CONLIN_SIGMA = float(_FIXTURE["sigma"])
PIXEL = load_pixel_csv()


def conlin(logLik=0.0, sigma=None):
    return ConLin(
        Xy=CONLIN_XY.copy(),
        dims=CONLIN_DIMS,
        logLik=logLik,
        sigma=CONLIN_SIGMA if sigma is None else sigma,
    )

def one():
    rs = reStruct({"Dog": "~day", "Side": "~1"}, data=PIXEL)
    rs1 = Initialize(rs, PIXEL, conLin=conlin())
    rs2 = Initialize(rs1, PIXEL, conLin=conlin())
    return np.concatenate([np.asarray(logDet(rs1), dtype=np.float64), np.asarray(logDet(rs2), dtype=np.float64)])


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
