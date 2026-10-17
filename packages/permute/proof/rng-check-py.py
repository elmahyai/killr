from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np  # noqa: E402
from shuffle_harness import Case, run_proof  # noqa: E402
from permute._rng import sample_int, unif_rand  # noqa: E402

OUT = Path(__file__).parents[1] / "docs" / "output"


def runif(k):
    return np.array([unif_rand() for _ in range(k)])


cases = [
    Case("rng_sample_10_10", 42, lambda: sample_int(10, 10)),
    Case("rng_runif_5", 42, lambda: runif(5)),
    Case("rng_sample_100_7", 123, lambda: sample_int(100, 7)),
    Case("rng_sample_50_50", 7, lambda: sample_int(50, 50)),
    Case("rng_sample_1000_50", 99, lambda: sample_int(1000, 50)),
    Case("rng_sample_hash_1e7", 2024, lambda: sample_int(10000001, 5)),
]
run_proof("rng-check", cases, OUT)
