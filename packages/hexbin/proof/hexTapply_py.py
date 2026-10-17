"""Python proof for hexTapply(). Run from the repository root after hexTapply_r.R:

    .venv/bin/python packages/hexbin/proof/hexTapply_py.py
"""

import numpy as np
from _proof_common import Report, load_ref, points_fixed, r_timing, time_median  # noqa: E402

from hexbin.hexbin import hexbin  # noqa: E402
from hexbin.hexTapply import hexTapply  # noqa: E402

NAME = "hexTapply"


def record(rep, ref, prefix, result):
    keys = np.array(sorted(result.keys()), dtype=np.float64)
    vals = np.array([result[int(k)] for k in keys], dtype=np.float64)
    rep.num(ref, f"{prefix}.keys", keys)
    rep.num(ref, f"{prefix}.values", vals)


def main() -> bool:
    ref = load_ref(NAME)
    x, y = points_fixed(20000)
    rep = Report(NAME)
    h = hexbin(x, y, xbins=30, IDs=True)

    record(rep, ref, "case1", hexTapply(h, y, FUN=sum))
    record(rep, ref, "case2", hexTapply(h, x, FUN=np.mean))
    record(rep, ref, "case3", hexTapply(h, x, FUN=np.max))

    py_median = time_median(lambda: hexTapply(h, x, FUN=sum))
    return rep.write(r_timing(ref), py_median)


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
