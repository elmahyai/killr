from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from shuffle_harness import Case, run_proof  # noqa: E402
from permute import shuffleGrid  # noqa: E402

OUT = Path(__file__).parents[1] / "docs" / "output"
cases = [
    Case("sg_plain", 21, lambda: shuffleGrid(3, 4)),
    Case("sg_mirror", 22, lambda: shuffleGrid(3, 4, mirror=True)),
    Case("sg_mirror_2x2", 23, lambda: shuffleGrid(2, 2, mirror=True)),
    Case("sg_start", 24, lambda: shuffleGrid(4, 3, start_row=2, start_col=1)),
    Case("sg_flip", 25, lambda: shuffleGrid(3, 3, mirror=True, flip=[True, False])),
    Case("sg_flip_none", 26, lambda: shuffleGrid(3, 3, mirror=True, flip=[False, False])),
    Case("sg_flip_2x5", 27, lambda: shuffleGrid(2, 5, mirror=True, flip=[False, True])),
    Case("sg_mirror_start", 28, lambda: shuffleGrid(3, 5, mirror=True, start_row=3, start_col=4)),
]
run_proof("shuffleGrid", cases, OUT)
