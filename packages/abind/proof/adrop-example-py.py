import sys

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/abind")
from abind.abind import Array
from abind.adrop import adrop
from abind.asub import asub

out_path = "/home/ahmed/killr_projects/killr/packages/abind/docs/output/adrop-python.txt"


def r_show(value):
    if value is None:
        return "NULL"
    if isinstance(value, tuple):
        if len(value) == 1:
            return f"[1] {value[0]}"
        return "[1] " + " ".join(str(item) for item in value)
    if isinstance(value, list) and value and isinstance(value[0], list):
        lines = []
        for index, margin in enumerate(value, start=1):
            lines.append(f"[[{index}]]")
            if margin is None:
                lines.append("NULL")
            else:
                lines.append("[1] " + " ".join(f'"{item}"' for item in margin))
        return "\n".join(lines)
    if isinstance(value, list):
        return "[1] " + " ".join(f'"{item}"' for item in value)
    return str(value)


x = Array(
    np.arange(1, 25, dtype=float).reshape((2, 3, 4), order="F"),
    dimnames=[list("ab"), list("ABC"), list("wxyz")],
)
scalar = asub(asub(asub(x, 1, 1, drop=False), 1, 2, drop=False), 1, 3, drop=False)
lines = [
    str(adrop(asub(x, 1, 1, drop=False), drop=1)),
    str(adrop(asub(x, 1, 2, drop=False), drop=2)),
    str(adrop(asub(x, 1, 3, drop=False), drop=3)),
    str(adrop(scalar, drop=1)),
    str(adrop(scalar, drop=2)),
    str(adrop(scalar, drop=3)),
    str(adrop(scalar, drop=[1, 2])),
    str(adrop(scalar, drop=[1, 2], one_d_array=True)),
    str(adrop(scalar, drop=[1, 2], named_vector=False)),
    r_show(adrop(scalar, drop=[1, 2], one_d_array=True)._r_dim),
    r_show(adrop(scalar, drop=[1, 2], one_d_array=True).dimnames),
    r_show(adrop(scalar, drop=[1, 2], one_d_array=True).names),
    r_show(adrop(scalar, drop=[1, 2])._r_dim),
    r_show(adrop(scalar, drop=[1, 2]).dimnames),
    r_show(adrop(scalar, drop=[1, 2]).names),
]
with open(out_path, "w", encoding="utf-8") as handle:
    handle.write("\n".join(lines) + "\n")
