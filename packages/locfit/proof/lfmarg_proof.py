"""Proof: lfmarg against R locfit 1.5-9.12 on the fixed cases in locfit10_r.R."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _locfit10 as L  # noqa: E402

mod = L.load_translated()
from locfit_translated.lfmarg import lfmarg  # noqa: E402


def main():
    numeric = lambda: lfmarg([0, 1, 2, 3], m=[5, 4])  # noqa: E731
    obj = lambda: lfmarg({"mi": {"d": 2}, "box": [-1, 0, 1, 2]}, m=[3, 6])  # noqa: E731
    diffs = {}
    for tag, call in (("1", numeric), ("2", obj)):
        got = call()
        for i, part in enumerate(("a", "b")):
            diffs[f"{tag}{part}"] = L.max_diff(got[i], L.ref_vec(f"lfmarg_{tag}{part}"))
            L.save(f"lfmarg_{tag}{part}", got[i])
    ms = L.timed_ms(numeric)
    ok = L.finish("lfmarg", diffs, ms)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
