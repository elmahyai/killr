from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np  # noqa: E402
from shuffle_harness import Case, run_proof  # noqa: E402
import permute  # noqa: E402
from permute import how, Within, Plots, allPerms  # noqa: E402

OUT = Path(__file__).parents[1] / "docs" / "output"
mat = allPerms(4, how(within=Within(type="free")))
cases = [
    Case("perm_free", 81, lambda: permute.permute(1, 6, how(within=Within(type="free")))),
    Case("perm_series_mirror", 82, lambda: permute.permute(1, 10, how(within=Within(type="series", mirror=True)))),
    Case("perm_grid", 83, lambda: permute.permute(1, 8, how(within=Within(type="grid", nrow=2, ncol=4)))),
    Case("perm_plots_free", 84, lambda: permute.permute(1, 8, how(plots=Plots(strata=np.repeat([1, 2, 3, 4], 2), type="free"), within=Within(type="none")))),
    Case("perm_blocks_free", 85, lambda: permute.permute(1, 8, how(blocks=np.repeat([1, 2], 4), within=Within(type="free")))),
    Case("perm_plots_free_within_free", 86, lambda: permute.permute(1, 8, how(plots=Plots(strata=np.repeat([1, 2], 4), type="free"), within=Within(type="free")))),
    Case("perm_complete_row2", 87, lambda: permute.permute(2, 4, how(complete=True, all_perms=mat))),
    Case("perm_within_none", 88, lambda: permute.permute(3, 5, how(within=Within(type="none")))),
]
run_proof("permute-rng", cases, OUT)
