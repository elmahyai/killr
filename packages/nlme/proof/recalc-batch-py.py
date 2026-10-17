import statistics
import sys
import time
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if "nlme" not in sys.modules:
    _pkg = types.ModuleType("nlme")
    _pkg.__path__ = [str(ROOT / "nlme")]
    sys.modules["nlme"] = _pkg

from nlme.corcompsymm import corCompSymm, initialize as init_comp  # noqa: E402
from nlme.corsymm import corSymm, initialize as init_symm  # noqa: E402
from nlme.glsapvar import ConLin  # noqa: E402
from nlme.recalc import proof_values, recalc  # noqa: E402
from nlme.var_ident import _NlmeFrame, initialize, varIdent  # noqa: E402

SUBJECT = {"Subject": ["a", "a", "a", "a", "b", "b", "b", "b", "c", "c", "c"]}


def vdata():
    return _NlmeFrame(
        {
            "y": np.arange(1, 10, dtype=np.float64),
            "grp": np.array(["A", "A", "B", "B", "C", "C", "A", "B", "C"], dtype=object),
        }
    )


def one():
    data = vdata()
    vf1 = initialize(varIdent(value={"B": 2.0, "C": 3.0}, form="~1 | grp"), data)
    vf2 = initialize(varIdent(value={"B": 1.5, "C": 0.5}, form="~1 | grp"), data)
    con_lin = ConLin(
        Xy=np.arange(1, 19, dtype=np.float64).reshape(9, 2, order="F"),
        dims={"N": 9, "p": 2},
        logLik=0.5,
    )
    con_cor = ConLin(
        Xy=np.arange(1, 23, dtype=np.float64).reshape(11, 2, order="F"),
        dims={"N": 11, "p": 2},
        logLik=0.5,
    )
    cc = init_comp(corCompSymm(0.5, form="~ 1 | Subject"), SUBJECT)
    cs = init_symm(corSymm([0.3, 0.1, 0.2, 0.05, 0.1, 0.25], form="~ 1 | Subject"), SUBJECT)
    return np.concatenate(
        [
            proof_values(recalc(vf1, con_lin)),
            proof_values(recalc([vf1, vf2], con_lin)),
            proof_values(recalc(cc, con_cor)),
            proof_values(recalc(cs, con_cor)),
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
