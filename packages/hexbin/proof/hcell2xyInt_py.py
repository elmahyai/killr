"""Python proof for hcell2xyInt(). Run from the repository root after hcell2xyInt_r.R:

    .venv/bin/python packages/hexbin/proof/hcell2xyInt_py.py
"""

from _proof_common import Report, load_ref, points_fixed, r_timing, time_median  # noqa: E402

from hexbin.hcell2xyInt import hcell2xyInt  # noqa: E402
from hexbin.hexbin import hexbin  # noqa: E402

NAME = "hcell2xyInt"


def main() -> bool:
    ref = load_ref(NAME)
    x, y = points_fixed(20000)
    rep = Report(NAME)
    h = hexbin(x, y, xbins=30, IDs=True)
    h2 = hexbin(x, y, xbins=12, shape=0.8)

    r1 = hcell2xyInt(h)
    rep.num(ref, "case1.i", r1["i"])
    rep.num(ref, "case1.j", r1["j"])

    r2 = hcell2xyInt(h2)
    rep.num(ref, "case2.i", r2["i"])
    rep.num(ref, "case2.j", r2["j"])

    r3 = hcell2xyInt(xbins=30, xbnds=(-5, 5), ybnds=(-3, 3), shape=1)
    rep.num(ref, "case3.i", r3["i"])
    rep.num(ref, "case3.j", r3["j"])

    r4 = hcell2xyInt(xbins=12, xbnds=(-5, 5), ybnds=(-3, 3), shape=0.8)
    rep.num(ref, "case4.i", r4["i"])
    rep.num(ref, "case4.j", r4["j"])

    py_median = time_median(lambda: hcell2xyInt(h))
    return rep.write(r_timing(ref), py_median)


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
