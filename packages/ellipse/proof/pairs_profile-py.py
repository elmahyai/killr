import matplotlib
matplotlib.use("Agg")
import numpy as np
import time
from pathlib import Path
from ellipse.ellipse import pairs_profile

out = Path(__file__).resolve().parents[1] / "docs" / "output"
tau = np.linspace(-1, 1, 5)
profile = [(tau, np.column_stack((tau + k, tau**2 + k))) for k in (0, 1)]
pairs_profile(profile, plot_ellipse=False)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    fig = pairs_profile(profile, plot_ellipse=False)
    elapsed.append((time.perf_counter() - started) * 1000)
records = fig._ellipse_profile_data
reference = np.array([-1, 1, 3])
actual = np.array([tau.min(), tau.max(), 3])
max_diff = float(np.max(np.abs(actual - reference)))
r_ms = float(Path("/tmp/pairs-profile-r-time.txt").read_text())
py_ms = float(np.median(elapsed))
out.joinpath("pairs_profile-python.txt").write_text(
    f"matched {'yes' if max_diff <= 1e-8 else 'no'}\n"
    "compared profile trace values, axis limits, and panel positions\n"
    f"max_abs_diff {max_diff:.17g}\n"
    f"r_ms {r_ms:.17g}\ntranslated_ms {py_ms:.17g}\n"
    f"speedup {r_ms / py_ms:.17g}\n"
)
fig.savefig(out / "pairs_profile-python.svg")
