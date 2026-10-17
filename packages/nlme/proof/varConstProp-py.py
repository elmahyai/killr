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
from nlme.varconstprop import proof_values, varConstProp


def one():
    a = varConstProp(const=1.2, prop=0.2, form="~age | Sex")
    b = varConstProp(const=2, prop=0.5)
    cc = varConstProp(const=3, prop=0.2, fixed={"const": 2})
    return np.concatenate([proof_values(a), proof_values(b), proof_values(cc)])


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
