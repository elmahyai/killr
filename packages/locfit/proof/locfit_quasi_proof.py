"""Proof: locfit.quasi against R locfit 1.5-9.12.

Blocked: the weight update needs fitted values (R's sfitted), which crates/locfit
does not return. This script runs the translated function and records the reason.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _locfit10 as L  # noqa: E402

L.load_translated()
from locfit_translated.locfit_quasi import locfit_quasi  # noqa: E402


def main():
    d = L.inputs()
    try:
        locfit_quasi(d["x1"], d["y1"], alpha=0.7, deg=2, kern="tricube", kt="sph",
                     ev={"type": "data"})
        L.blocked("locfit_quasi", "unexpected: ran without fitted values")
        sys.exit(1)
    except NotImplementedError as exc:
        L.blocked("locfit_quasi", f"sfitted (fitted values) in crates/locfit: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
