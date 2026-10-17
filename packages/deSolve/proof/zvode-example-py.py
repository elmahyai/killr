import sys

ROOT = "/home/ahmed/killr_projects/killr"
sys.path.insert(0, f"{ROOT}/packages/deSolve")

from deSolve.zvode import zvode


def spin(t, y, parms):
    return [1j * parms["w"] * y[0]]


out = zvode({"z": 1 + 0j}, list(range(0, 7, 2)), spin, {"w": 1.0})
print(out)
