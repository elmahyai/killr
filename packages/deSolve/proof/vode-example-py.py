import sys

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/deSolve")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/crates/dvode")

from deSolve.vode import vode


def logist(t, x, parms):
    r = parms["r"]
    k = parms["K"]
    return [r * x[0] * (1.0 - x[0] / k)]


print(vode({"N": 0.1}, list(range(0, 11, 2)), logist, {"r": 0.5, "K": 100}))
