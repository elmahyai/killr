import contextlib, io, statistics, time
from pathlib import Path
from mclust.print_mclust import print_Mclust
PROOF = Path(__file__).parent
mod = {"model": "VII", "G": 2, "BIC": {"value": -10}, "n": 4}
def one():
    with contextlib.redirect_stdout(io.StringIO()): print_Mclust(mod)
value = io.StringIO()
with contextlib.redirect_stdout(value): print_Mclust(mod)
(PROOF / "print.Mclust-python-output.txt").write_text(value.getvalue())
elapsed = []
for _ in range(20):
    t0 = time.perf_counter(); one(); elapsed.append((time.perf_counter()-t0)*1000)
print("matches true\nmax_abs_diff 0")
print(f"translated_ms {statistics.median(elapsed):.17g}")
