"""Python proof for hexList(). Run from the repository root after hexList_r.R:

    .venv/bin/python packages/hexbin/proof/hexList_py.py
"""

import numpy as np
from _proof_common import Report, load_ref, points_fixed, r_timing, time_median  # noqa: E402

from hexbin.hexList import hexList  # noqa: E402

NAME = "hexList"


def record_list(rep, ref, prefix, hl):
    rep.num(ref, f"{prefix}.n", hl.n)
    rep.num(ref, f"{prefix}.Xbnds", hl.Xbnds)
    rep.num(ref, f"{prefix}.Ybnds", hl.Ybnds)
    rep.num(ref, f"{prefix}.Xbins", hl.Xbins)
    rep.num(ref, f"{prefix}.Shape", hl.Shape)
    rep.num(ref, f"{prefix}.CntBnds", hl.CntBnds)
    rep.text(ref, f"{prefix}.Bnames", "|".join(hl.Bnames))
    for i, h in enumerate(hl.hbins, start=1):
        p = f"{prefix}.hb{i}"
        rep.num(ref, f"{p}.cell", h.cell)
        rep.num(ref, f"{p}.count", h.count)
        rep.num(ref, f"{p}.xcm", h.xcm)
        rep.num(ref, f"{p}.ycm", h.ycm)
        rep.num(ref, f"{p}.xbins", h.xbins)
        rep.num(ref, f"{p}.shape", h.shape)
        rep.num(ref, f"{p}.xbnds", h.xbnds)
        rep.num(ref, f"{p}.ybnds", h.ybnds)
        rep.num(ref, f"{p}.dimen", h.dimen)
        rep.num(ref, f"{p}.n", h.n)
        rep.num(ref, f"{p}.ncells", h.ncells)


def main() -> bool:
    ref = load_ref(NAME)
    x, y = points_fixed(20000)
    k = np.arange(1, x.size + 1, dtype=np.float64)
    labels = np.array(["alpha", "beta", "gamma"])
    given = labels[(k % 3).astype(int)]
    rep = Report(NAME)

    record_list(rep, ref, "case1", hexList(x, y, given, xbins=30))
    record_list(rep, ref, "case2", hexList(x, y, given, xbins=12, shape=0.8, xbnds=(-5, 5), ybnds=(-3, 3)))

    py_median = time_median(lambda: hexList(x, y, given, xbins=30))
    return rep.write(r_timing(ref), py_median)


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
