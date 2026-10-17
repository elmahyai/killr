"""RNG check for the sim group: Python draws against the R record for fixed seeds.

Run after proof/sim-rng-check-r.R, from packages/mclust:
    Rscript proof/sim-rng-check-r.R && python3 proof/sim-rng-check-py.py
"""

import sys
from pathlib import Path

PROOF = Path(__file__).resolve().parent
sys.path.insert(0, str(PROOF))
sys.path.insert(0, str(PROOF.parent))

from sim_proof_common import OUT, compare  # noqa: E402
from mclust._sim_common import norm_rand, sample_labels, seed_if_given, unif  # noqa: E402
from sim_proof_common import _fmt  # noqa: E402


def main():
    lines = []
    for s in (1, 42, 20260917):
        seed_if_given(s)
        lines.append(f"seed\t{s}")
        lines.append("\t".join(["unif"] + [_fmt(unif()) for _ in range(5)]))
        seed_if_given(s)
        lines.append("\t".join(["rnorm"] + [_fmt(norm_rand()) for _ in range(20)]))
        seed_if_given(s)
        fill = [_fmt(norm_rand()) for _ in range(12)]  # column-major fill of a 4 x 3 matrix
        lines.append("\t".join(["rnormfill"] + fill))
        seed_if_given(s)
        labels = sample_labels(3, 50, [0.2, 0.3, 0.5])
        lines.append("\t".join(["sample"] + [str(int(v)) for v in labels]))
    ref = (OUT / "sim-rng-check-r.txt").read_text().splitlines()
    matches, max_diff = compare(ref, lines)
    summary = [
        "# sim-rng-check",
        f"# matches\t{'yes' if matches else 'no'}",
        f"# max_abs_diff\t{max_diff:.3g}",
    ]
    (OUT / "sim-rng-check-py.txt").write_text("\n".join(summary + lines) + "\n")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
