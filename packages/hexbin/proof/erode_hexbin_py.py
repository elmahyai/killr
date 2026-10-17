"""Python proof for erode.hexbin (erode_hexbin). Run from the repository root after erode_hexbin_r.R:

    .venv/bin/python packages/hexbin/proof/erode_hexbin_py.py
"""

from _proof_common import Report, load_ref, points_fixed, r_timing, time_median  # noqa: E402

from hexbin.erode_hexbin import erode_hexbin  # noqa: E402
from hexbin.hexbin import hexbin  # noqa: E402

NAME = "erode_hexbin"


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
    h3 = hexbin(x, y, xbins=30)

    record(rep, ref, "case1", erode_hexbin(h, 0.5))
    record(rep, ref, "case2", erode_hexbin(h2, 0.75))
    record(rep, ref, "case3", erode_hexbin(h3, 2))
    record(rep, ref, "case4", erode_hexbin(h, 0.1))

    py_median = time_median(lambda: erode_hexbin(h, 0.5))
    return rep.write(r_timing(ref), py_median)


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
