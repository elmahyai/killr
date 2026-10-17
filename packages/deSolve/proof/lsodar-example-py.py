import sys
from pathlib import Path

ROOT = Path("/home/ahmed/killr_projects/killr")
sys.path.insert(0, str(ROOT / "packages" / "deSolve"))

import numpy as np

from deSolve.lsodar import lsodar


def logist(t, x, parms):
    r = parms["r"]
    k = parms["K"]
    dx = r * x[0] * (1 - x[0] / k)
    return ([dx],)


out = lsodar({"N": 0.1}, np.arange(0, 11, 2, dtype=float), logist, {"r": 0.5, "K": 100})
print(out)
