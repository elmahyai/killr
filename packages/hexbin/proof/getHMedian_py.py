"""Python proof for getHMedian(). Run from the repository root after getHMedian_r.R:

    .venv/bin/python packages/hexbin/proof/getHMedian_py.py
"""

from _proof_common import Report, load_ref, points_fixed, r_timing, time_median  # noqa: E402

from hexbin.erode import erode  # noqa: E402
from hexbin.getHMedian import getHMedian  # noqa: E402
from hexbin.hexbin import hexbin  # noqa: E402

NAME = "getHMedian"


def main() -> bool:
    ref = load_ref(NAME)
    x, y = points_fixed(20000)
    rep = Report(NAME)
    h = hexbin(x, y, xbins=30, IDs=True)
    h2 = hexbin(x, y, xbins=12, shape=0.8)

    m1 = getHMedian(erode(h, 0.5))
    rep.num(ref, "case1.x", m1["x"])
    rep.num(ref, "case1.y", m1["y"])

    m2 = getHMedian(erode(h2, 0.25))
    rep.num(ref, "case2.x", m2["x"])
    rep.num(ref, "case2.y", m2["y"])

    m3 = getHMedian(erode(h, 0.9))
    rep.num(ref, "case3.x", m3["x"])
    rep.num(ref, "case3.y", m3["y"])

    e = erode(h, 0.5)
    py_median = time_median(lambda: getHMedian(e))
    return rep.write(r_timing(ref), py_median)


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
