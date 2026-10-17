"""Proof: lp against R locfit 1.5-9.12 (values and the alpha and deg attributes)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _locfit10 as L  # noqa: E402

L.load_translated()
from locfit_translated.lp import lp  # noqa: E402


def main():
    d = L.inputs()
    xa, xb = d["xa"], d["xb"]
    case1 = lambda: lp(xa, xb)  # noqa: E731
    case2 = lambda: lp(xa, nn=0.4, h=0.1, adpen=2, deg=1)  # noqa: E731
    diffs = {}
    for tag, call in (("1", case1), ("2", case2)):
        out = call()
        diffs[f"{tag}_values"] = L.max_diff(out, L.ref(f"lp_{tag}_x"))
        diffs[f"{tag}_alpha"] = L.max_diff(out.alpha, L.ref_vec(f"lp_{tag}_alpha"))
        diffs[f"{tag}_deg"] = L.max_diff([out.deg], L.ref_vec(f"lp_{tag}_deg"))
        L.save(f"lp_{tag}_x", out)
    ms = L.timed_ms(case1)
    ok = L.finish("lp", diffs, ms)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
