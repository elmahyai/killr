import sys

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/abind")
from abind.abind import Array
from abind.afill_replacement import afill_replacement

out_path = "/home/ahmed/killr_projects/killr/packages/abind/docs/output/afill-replacement-python.txt"
lines = []

x = Array(np.zeros((4, 3), order="F"), dimnames=[list("abcd"), list("XYZ")])
lines.append(str(x))
y = Array(
    np.arange(1, 5, dtype=float).reshape((2, 2), order="F"),
    dimnames=[list("bc"), list("YZ")],
)
lines.append(str(y))
afill_replacement(x, value=y)
lines.append(str(x))

x3 = Array(
    np.zeros((2, 4, 3), order="F"),
    dimnames=[list("AB"), list("abcd"), list("XYZ")],
)
y3 = Array(
    np.arange(1, 5, dtype=float).reshape((2, 2), order="F"),
    dimnames=[list("bc"), list("YZ")],
)
afill_replacement(x3, 1, None, None, value=y3)
lines.append(str(Array(x3.data[0:1, :, :], dimnames=[x3.dimnames[0][0:1], x3.dimnames[1], x3.dimnames[2]])))
lines.append(str(Array(x3.data[1:2, :, :], dimnames=[x3.dimnames[0][1:2], x3.dimnames[1], x3.dimnames[2]])))

with open(out_path, "w", encoding="utf-8") as handle:
    handle.write("\n".join(lines) + "\n")
