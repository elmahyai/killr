import sys

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/deSolve")
from deSolve.rk4 import rk4
from deSolve.timestep import timestep


def mod(t, x, parms):
    r = float(parms["r"])
    k = float(parms["K"])
    dx = r * x[0] * (1.0 - x[0] / k)
    return {"": np.array([dx], dtype=float), "prev": timestep(True), "curr": timestep(False)}


out = rk4({"N": 0.1}, np.arange(0.0, 12.0, 2.0), mod, {"r": 0.5, "K": 100.0})
print("after_rk4_timestep_prev")
print(timestep(True))
print("after_rk4_timestep_curr")
print(timestep(False))
print("global_prev_column")
print(out.data[:, out.colnames.index("prev")])
print("global_curr_column")
print(out.data[:, out.colnames.index("curr")])
