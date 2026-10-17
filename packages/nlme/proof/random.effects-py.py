import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
_py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
_site = ROOT / ".venv" / "lib" / _py_ver / "site-packages"
sys.path[:0] = [
    str(ROOT / "packages" / "nlme"),
    str(_site),
    str(ROOT / "crates" / "onecomp"),
]
from nlme.augpred_fixtures import orthodont_fixtures
from nlme.lmlistformula import lmList_formula
from nlme.ranef import random_effects

FIXTURES = orthodont_fixtures()
# lmList(Orthodont) keeps the factor-level order of Subject, as R does.
FM1 = lmList_formula("distance ~ age | Subject", data=FIXTURES.data)


def one():
    parts = [
        random_effects(FIXTURES.fm2).as_matrix(),
        random_effects(FM1).as_matrix(),
    ]
    return np.concatenate([np.asarray(part, dtype=np.float64).reshape(-1, order="F") for part in parts])


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
