"""Python proof for inout.hex() (inout_hex). Run from the repository root after inout_hex_r.R:

    .venv/bin/python packages/hexbin/proof/inout_hex_py.py
"""

from _proof_common import Report, load_ref, points_fixed, r_timing, time_median  # noqa: E402

from hexbin.hexbin import hexbin  # noqa: E402
from hexbin.inout_hex import inout_hex  # noqa: E402

NAME = "inout_hex"


def main() -> bool:
    ref = load_ref(NAME)
    x, y = points_fixed(20000)
    rep = Report(NAME)

    h = hexbin(x, y, xbins=30, IDs=True)
    rep.num(ref, "case1", inout_hex(h, 3))
    rep.num(ref, "case2", inout_hex(h, 10))

    h2 = hexbin(x, y, xbins=12, shape=0.8, IDs=True)
    rep.num(ref, "case3", inout_hex(h2, 5))

    xna = x.copy()
    xna[[4, 76]] = float("nan")
    hna = hexbin(xna, y, xbins=30, IDs=True)
    rep.num(ref, "case4", inout_hex(hna, 5))

    py_median = time_median(lambda: inout_hex(h, 5))
    return rep.write(r_timing(ref), py_median)


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
