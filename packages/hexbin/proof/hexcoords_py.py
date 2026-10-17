"""Python proof for hexcoords(). Run from the repository root after hexcoords_r.R:

    .venv/bin/python packages/hexbin/proof/hexcoords_py.py
"""

import math

from _proof_common import Report, load_ref, r_timing, time_median  # noqa: E402

from hexbin.hexcoords import hexcoords  # noqa: E402

NAME = "hexcoords"


def main() -> bool:
    ref = load_ref(NAME)
    rep = Report(NAME)

    a = hexcoords(dx=0.5, n=3)
    rep.num(ref, "case1.x", a["x"])
    rep.num(ref, "case1.y", a["y"])
    rep.num(ref, "case1.no_sep", float(a["no_sep"]))

    b = hexcoords(dx=0.3, dy=0.2, n=2, sep=math.nan)
    rep.num(ref, "case2.x", b["x"])
    rep.num(ref, "case2.y", b["y"])
    rep.num(ref, "case2.no_sep", float(b["no_sep"]))

    c2 = hexcoords(dx=1, n=1, sep=0)
    rep.num(ref, "case3.x", c2["x"])
    rep.num(ref, "case3.y", c2["y"])
    rep.num(ref, "case3.no_sep", float(c2["no_sep"]))

    d = hexcoords(dx=2.5)
    rep.num(ref, "case4.x", d["x"])
    rep.num(ref, "case4.y", d["y"])

    py_median = time_median(lambda: hexcoords(dx=0.5, dy=0.3, n=20000))
    return rep.write(r_timing(ref), py_median)


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
