"""Python proof for hexbin(). Run from the repository root after hexbin_r.R:

    .venv/bin/python packages/hexbin/proof/hexbin_py.py
"""

import numpy as np

from _proof_common import Report, load_ref, points_fixed, r_timing, time_median  # noqa: E402

from hexbin.hexbin import hexbin  # noqa: E402

NAME = "hexbin"


def main() -> bool:
    ref = load_ref(NAME)
    x, y = points_fixed(20000)
    rep = Report(NAME)

    cases = {
        "case1": hexbin(x, y, xbins=30, shape=1, IDs=True),
        "case2": hexbin(x, y, xbins=12, shape=0.8),
    }
    xna = x.copy()
    xna[[4, 76]] = np.nan
    yna = y.copy()
    yna[299] = np.nan
    cases["case3"] = hexbin(xna, yna, xbins=30, shape=1, IDs=True)
    cases["case4"] = hexbin(x, y, xbins=20, shape=1.2, xbnds=(-6, 6), ybnds=(-4, 4))

    for prefix, h in cases.items():
        rep.num(ref, f"{prefix}.cell", h.cell)
        rep.num(ref, f"{prefix}.count", h.count)
        rep.num(ref, f"{prefix}.xcm", h.xcm)
        rep.num(ref, f"{prefix}.ycm", h.ycm)
        rep.num(ref, f"{prefix}.xbins", h.xbins)
        rep.num(ref, f"{prefix}.shape", h.shape)
        rep.num(ref, f"{prefix}.xbnds", h.xbnds)
        rep.num(ref, f"{prefix}.ybnds", h.ybnds)
        rep.num(ref, f"{prefix}.dimen", h.dimen)
        rep.num(ref, f"{prefix}.n", h.n)
        rep.num(ref, f"{prefix}.ncells", h.ncells)
        if h.cID is not None:
            rep.num(ref, f"{prefix}.cID", h.cID)

    py_median = time_median(lambda: hexbin(x, y, xbins=30, shape=1))
    ok = rep.write(r_timing(ref), py_median)
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
