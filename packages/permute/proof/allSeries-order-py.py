from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from shuffle_harness import Case, run_proof  # noqa: E402
import permute  # noqa: E402
from permute.core import allSeries  # noqa: E402

OUT = Path(__file__).parents[1] / "docs" / "output"
cases = [
    Case("aseries_n4", 0, lambda: allSeries(4, 4, mirror=False)),
    Case("aseries_n4_mirror", 0, lambda: allSeries(4, 8, mirror=True)),
    Case("aseries_n5", 0, lambda: allSeries(5, 5, mirror=False)),
    Case("aseries_n6_mirror", 0, lambda: allSeries(6, 12, mirror=True)),
    Case("aseries_allperms_mirror", 0, lambda: permute.allPerms(4, permute.how(within=permute.Within(type="series", mirror=True)))),
]
run_proof("allSeries-order", cases, OUT)
