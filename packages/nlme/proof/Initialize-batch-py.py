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

from nlme.corcompsymm import coef as coef_cc, corCompSymm  # noqa: E402
from nlme.corlin import corLin, corMatrix as corlin_matrix  # noqa: E402
from nlme.corratio import corMatrix as corratio_matrix, corRatio  # noqa: E402
from nlme.corspher import corMatrix as corspher_matrix, corSpher  # noqa: E402
from nlme.corsymm import coef as coef_symm, corSymm  # noqa: E402
from nlme.initialize import Initialize  # noqa: E402
from nlme.var_ident import _NlmeFrame, coef as coef_vi, var_weights as vw_vi, varIdent  # noqa: E402
from nlme.var_power import coef as coef_vp, var_weights as vw_vp, varPower  # noqa: E402

DAT = {"x": [0.0, 1.0, 0.5, 2.0], "y": [0.0, 0.0, 1.0, 0.5]}
SUBJ = {"Subject": ["a", "a", "a", "a", "b", "b", "b", "b", "c", "c", "c"]}


def vdat():
    return _NlmeFrame(
        {
            "y": np.arange(1, 10, dtype=np.float64),
            "grp": np.array(["A", "A", "B", "B", "C", "C", "A", "B", "C"], dtype=object),
        }
    )


def pdat():
    return _NlmeFrame(
        {
            "y": np.arange(1, 7, dtype=np.float64),
            "x": np.array([1.2, 2.5, 3.1, 4.0, 5.5, 6.3], dtype=np.float64),
            "grp": np.array(["A", "A", "B", "B", "A", "B"], dtype=object),
        }
    )


def flat(values):
    return np.ravel(np.asarray(values, dtype=np.float64), order="F")


def one():
    lin = Initialize(corLin(2.5, form="~ x + y", metric="eu"), DAT)
    rat = Initialize(corRatio(1.8, form="~ x + y", metric="eu"), DAT)
    sph = Initialize(corSpher(2.5, form="~ x + y", metric="eu"), DAT)
    cs0 = Initialize(corSymm(form="~ 1 | Subject"), SUBJ)
    cs1 = Initialize(corSymm([0.3, 0.1, 0.2, 0.05, 0.1, 0.25], form="~ 1 | Subject"), SUBJ)
    cc0 = Initialize(corCompSymm(0.5, form="~ 1 | Subject"), SUBJ)
    cc1 = Initialize(corCompSymm(-0.2, form="~ 1 | Subject"), SUBJ)
    vf1 = Initialize(varIdent(value={"B": 2.0, "C": 3.0}, form="~1 | grp"), vdat())
    vf2 = Initialize(varIdent(value={"B": 2.0}, fixed={"C": 3.0}, form="~1 | grp"), vdat())
    vf3 = Initialize(varIdent(form="~1"), vdat())
    pw1 = Initialize(varPower(0.35, form="~x"), pdat())
    pw2 = Initialize(varPower(value={"A": 0.3, "B": 0.6}, form="~x|grp"), pdat())
    parts = [
        flat(corlin_matrix(lin)),
        flat(corratio_matrix(rat)),
        flat(corspher_matrix(sph)),
        flat(cs0.value),
        flat(coef_symm(cs0, unconstrained=True).values),
        flat(cs0.factor),
        np.asarray([cs0.log_det]),
        np.asarray([cs0.max_cov]),
        flat(cs1.value),
        flat(coef_symm(cs1, unconstrained=False).values),
        np.asarray([cc0.value]),
        flat(coef_cc(cc0, unconstrained=True).values),
        np.asarray([cc0.inf]),
        flat(cc0.factor),
        np.asarray([cc0.log_det]),
        flat(coef_cc(cc0, unconstrained=False).values),
        np.asarray([cc1.value]),
        np.asarray([cc1.inf]),
        flat(cc1.factor),
        np.asarray([cc1.log_det]),
        flat(coef_cc(cc1, unconstrained=False).values),
        flat(coef_vi(vf1, unconstrained=True).values),
        flat(coef_vi(vf1, unconstrained=False, allCoef=True).values),
        flat(vw_vi(vf1)),
        np.asarray([vf1.log_lik]),
        flat(coef_vi(vf2, unconstrained=True).values),
        flat(coef_vi(vf2, unconstrained=False, allCoef=True).values),
        flat(vw_vi(vf2)),
        np.asarray([vf2.log_lik]),
        flat(coef_vi(vf3, unconstrained=True).values),
        flat(vw_vi(vf3)),
        np.asarray([vf3.log_lik]),
        flat(coef_vp(pw1, unconstrained=True, allCoef=False).values),
        flat(coef_vp(pw1, unconstrained=True, allCoef=True).values),
        flat(vw_vp(pw1)),
        np.asarray([pw1.log_lik]),
        flat(coef_vp(pw2, unconstrained=True, allCoef=False).values),
        flat(coef_vp(pw2, unconstrained=True, allCoef=True).values),
        flat(vw_vp(pw2)),
        np.asarray([pw2.log_lik]),
    ]
    return np.concatenate([np.ravel(p).astype(np.float64) for p in parts])


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
