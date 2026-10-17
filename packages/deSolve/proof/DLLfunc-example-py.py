import sys

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/deSolve")
from deSolve.DLLfunc import DLLfunc

parameters = np.array(
    [
        0.125, 0.001, -0.125 / 150, 0.0, 0.136, 1.0, 0.05, 0.15, 0.075, 0.23,
        0.0001, 0.4, 0.06, 0.01, 0.2, 10.0, 1.0, 250.0, 15.0,
    ],
    dtype=np.float64,
)
state = np.array([6.0, 20.0, 5.0, 1.0], dtype=np.float64)
out = DLLfunc(
    func="aquaphy",
    times=10,
    y=state,
    parms=parameters,
    dllname="deSolve",
    initfunc="iniaqua",
    nout=6,
    outnames=["PAR", "TotalN", "PhotoSynthesis", "NCratio", "ChlCratio", "Chlorophyll"],
)
print("dy:", " ".join(f"{v:.8g}" for v in out["dy"]))
print("var:", " ".join(f"{v:.8g}" for v in np.asarray(out["var"])))
