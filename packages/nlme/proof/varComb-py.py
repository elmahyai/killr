import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.allcoef import varPower
from nlme.varcomb import VarFunc, varComb


@dataclass(slots=True)
class _VarIdentStandIn(VarFunc):
    """Minimal varIdent stand-in for the help-page example (not a full translation)."""

    form: str

    @property
    def classes(self) -> tuple[str, ...]:
        return ("varIdent", "varFunc")


def one():
    vf1 = varComb(_VarIdentStandIn("~1|Sex"), varPower(0.5))
    return np.asarray(
        [len(vf1), ord(vf1.names[0]), ord(vf1.names[1])],
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
