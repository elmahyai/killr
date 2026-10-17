"""Python proof for smooth.hexbin() (smooth_hexbin). Run from the repository root after smooth_hexbin_r.R:

    .venv/bin/python packages/hexbin/proof/smooth_hexbin_py.py
"""

from _proof_common import Report, load_ref, points_fixed, r_timing, time_median  # noqa: E402

from hexbin.hexbin import hexbin  # noqa: E402
from hexbin.smooth_hexbin import smooth_hexbin  # noqa: E402

NAME = "smooth_hexbin"


def record_smooth(rep, ref, prefix, s):
    rep.num(ref, f"{prefix}.cell", s.cell)
    rep.num(ref, f"{prefix}.count", s.count)
    rep.num(ref, f"{prefix}.xcm", s.xcm)
    rep.num(ref, f"{prefix}.ycm", s.ycm)
    rep.num(ref, f"{prefix}.xbins", s.xbins)
    rep.num(ref, f"{prefix}.xbnds", s.xbnds)
    rep.num(ref, f"{prefix}.ybnds", s.ybnds)
    rep.num(ref, f"{prefix}.dimen", s.dimen)
    rep.num(ref, f"{prefix}.wts", s.wts)
    rep.num(ref, f"{prefix}.n", s.n)
    rep.num(ref, f"{prefix}.ncells", s.ncells)


def main() -> bool:
    ref = load_ref(NAME)
    x, y = points_fixed(20000)
    rep = Report(NAME)
    h = hexbin(x, y, xbins=30)
    h2 = hexbin(x, y, xbins=12, shape=0.8)

    record_smooth(rep, ref, "case1", smooth_hexbin(h))
    record_smooth(rep, ref, "case2", smooth_hexbin(h, (10, 3, 1)))
    record_smooth(rep, ref, "case3", smooth_hexbin(h2, (48, 4, 1)))

    py_median = time_median(lambda: smooth_hexbin(h))
    return rep.write(r_timing(ref), py_median)


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
