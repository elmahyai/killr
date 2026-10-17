import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path("/home/ahmed/killr_projects/killr")
sys.path[:0] = [str(ROOT / "packages" / "deSolve"), str(ROOT / "crates" / "lagvalue")]

from deSolve.lagvalue import lagvalue, restore_hist  # noqa: E402

snap = json.loads((ROOT / "packages/deSolve/proof/lagvalue-hist.json").read_text())
restore_hist(snap)
v15 = np.asarray(lagvalue(1.5), dtype=float)
v152 = float(lagvalue(1.5, 2))
print(f"lagvalue(1.5): {' '.join(f'{x:.17g}' for x in v15)}")
print(f"lagvalue(1.5, 2): {v152:.17g}")
