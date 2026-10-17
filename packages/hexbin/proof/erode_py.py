"""Python proof for erode(). Run from the repository root after erode_r.R:

    .venv/bin/python packages/hexbin/proof/erode_py.py
"""

from _proof_common import Report, load_ref, points_fixed, r_timing, time_median  # noqa: E402

from hexbin.erode import erode  # noqa: E402
from hexbin.hexbin import hexbin  # noqa: E402

NAME = "erode"


def record(rep, ref, prefix, e):
    if isinstance(e, str):
        rep.text(ref, f"{prefix}.result", e)
        return
    rep.num(ref, f"{prefix}.cell", e.cell)
    rep.num(ref, f"{prefix}.count", e.count)
    rep.num(ref, f"{prefix}.eroded", e.eroded.astype(float))
    rep.num(ref, f"{prefix}.erode", e.erode)
    rep.num(ref, f"{prefix}.cdfcut", e.cdfcut)
    rep.num(ref, f"{prefix}.dimen", e.dimen)


def main() -> bool:
    ref = load_ref(NAME)
    x, y = points_fixed(20000)
    rep = Report(NAME)
    h = hexbin(x, y, xbins=30, IDs=True)
    h2 = hexbin(x, y, xbins=12, shape=0.8)

    record(rep, ref, "case1", erode(h, 0.5))
    record(rep, ref, "case2", erode(h, 0.9))
    record(rep, ref, "case3", erode(h, 1.5))
    record(rep, ref, "case4", erode(h2, 0.25))

    py_median = time_median(lambda: erode(h, 0.5))
    return rep.write(r_timing(ref), py_median)


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
