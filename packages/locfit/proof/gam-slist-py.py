"""Proof: gam.slist is an R character vector, not a function. Values only.

R reference: gam-slist-r.R (docs/output/gam_slist_r.txt). The Python value
is the list in locfit/gam_slist.py. No timing: it is not a function.

Run from the repository root:
    .venv/bin/python packages/locfit/proof/gam-slist-py.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("locfit_gam_slist", PKG / "locfit" / "gam_slist.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

want = (PKG / "docs" / "output" / "gam_slist_r.txt").read_text().splitlines()
got = ["TRUE"] + list(mod.gam_slist)
ok = want[0] == "TRUE" and want[1:] == got[1:]
line = f"gam.slist,matches={'yes' if ok else 'no'},values={len(got) - 1},python=locfit.gam_slist.gam_slist"
print(line)
(PKG / "docs" / "output" / "gam_slist_compare.txt").write_text(line + "\n")
sys.exit(0 if ok else 1)
