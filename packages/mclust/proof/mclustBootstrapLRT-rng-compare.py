"""Fixed-seed check of the ported generators against R's rnorm and runif.

Gate for mclustBootstrapLRT: the bootstrap draws from R's random stream, so the
ported norm_rand and unif_rand are used only if they match R within 1e-8.
Writes packages/mclust/docs/output/mclustBootstrapLRT-rng-compare.txt.
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")
from boot.rng import set_seed, unif  # noqa: E402

BIG = 134217728  # R's INVERSION rnorm constant
SEEDS = [42, 1, 2026]
N = 10000


def norm_rand():
    # Same formula as R's norm_rand (Inversion) and the MASS port.
    from boot.series import qnorm

    u1 = unif()
    u1 = int(BIG * u1) + unif()
    return qnorm(u1 / BIG)


R_CODE = (
    "for (s in c(42, 1, 2026)) { set.seed(s); "
    f"cat(sprintf('%.17g', rnorm({N})), '\\n'); "
    "set.seed(s); "
    f"cat(sprintf('%.17g', runif({N})), '\\n') }}"
)
raw = subprocess.run(["Rscript", "-e", R_CODE], capture_output=True, text=True, check=True).stdout
lines = [line.split() for line in raw.strip().splitlines()]

report = []
worst = 0.0
for k, seed in enumerate(SEEDS):
    r_norm = [float(v) for v in lines[2 * k]]
    r_unif = [float(v) for v in lines[2 * k + 1]]
    set_seed(seed)
    py_norm = [norm_rand() for _ in range(N)]
    set_seed(seed)
    py_unif = [unif() for _ in range(N)]
    dn = max(abs(a - b) for a, b in zip(r_norm, py_norm))
    du = max(abs(a - b) for a, b in zip(r_unif, py_unif))
    worst = max(worst, dn, du)
    report.append(f"seed {seed}: rnorm max_abs_diff {dn:.3g}, runif max_abs_diff {du:.3g}")

report.append(f"overall max_abs_diff {worst:.3g}; within 1e-8: {worst <= 1e-8}")
text = "\n".join(report) + "\n"
out = Path("/home/ahmed/killr_projects/killr/packages/mclust/docs/output/mclustBootstrapLRT-rng-compare.txt")
out.write_text(text)
sys.stdout.write(text)
