import contextlib
import io
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.print_hc import print_hc

proof_dir = Path(__file__).parent
hc_obj = {
    "call": 'hc(x, modelName = "E")',
    "modelName": "E",
    "use": "VARS",
    "dimensions": [4, 1],
}


def one():
    with contextlib.redirect_stdout(io.StringIO()):
        return print_hc(hc_obj)


value = io.StringIO()
with contextlib.redirect_stdout(value):
    print_hc(hc_obj)
(proof_dir / "print.hc-py-output.txt").write_text(value.getvalue())
reference = (proof_dir / "print.hc-r-output.txt").read_text()
max_abs_diff = 0 if value.getvalue() == reference else 1
one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(f"matches {max_abs_diff == 0}\nmax_abs_diff {max_abs_diff}")
print(f"translated_ms {statistics.median(elapsed):.17g}")
