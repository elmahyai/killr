"""Python proof for hcell2xy(). Run from the repository root after hcell2xy_r.R:

    .venv/bin/python packages/hexbin/proof/hcell2xy_py.py
"""

from _proof_common import Report, load_ref, points_fixed, r_timing, time_median  # noqa: E402

from hexbin.erode import erode  # noqa: E402
from hexbin.hcell2xy import hcell2xy  # noqa: E402
from hexbin.hexbin import hexbin  # noqa: E402

NAME = "hcell2xy"


def main() -> bool:
    ref = load_ref(NAME)
    x, y = points_fixed(20000)
    rep = Report(NAME)
    h = hexbin(x, y, xbins=30, IDs=True)
    h2 = hexbin(x, y, xbins=12, shape=0.8)
    e = erode(h, 0.5)

    xy1 = hcell2xy(h)
    rep.num(ref, "case1.x", xy1["x"])
    rep.num(ref, "case1.y", xy1["y"])

    xy2 = hcell2xy(h2)
    rep.num(ref, "case2.x", xy2["x"])
    rep.num(ref, "case2.y", xy2["y"])

    xy3 = hcell2xy(e)
    rep.num(ref, "case3.x", xy3["x"])
    rep.num(ref, "case3.y", xy3["y"])

    xy4 = hcell2xy(e, check_erosion=False)
    rep.num(ref, "case4.x", xy4["x"])
    rep.num(ref, "case4.y", xy4["y"])

    py_median = time_median(lambda: hcell2xy(h))
    return rep.write(r_timing(ref), py_median)


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
