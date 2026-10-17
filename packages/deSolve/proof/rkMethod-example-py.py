import sys

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/deSolve")
from deSolve.rkMethod import rkMethod

print(rkMethod())
print(rkMethod("rk45dp7"))
