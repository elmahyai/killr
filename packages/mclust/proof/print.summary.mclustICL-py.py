import contextlib
import io
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from mclust.icl_print import print_summary_mclust_icl

x = {"values": [10.]}


def one():
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        print_summary_mclust_icl(x)
    return output.getvalue()


value = one()
output_path = Path(__file__).parents[1] / "docs" / "output" / "print.summary.mclustICL.txt"
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(value)
reference = (Path(__file__).parent / "print.summary.mclustICL-r-output.txt").read_text()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
max_abs_diff = 0 if value == reference else 1
print(f"matches {max_abs_diff == 0}\nmax_abs_diff {max_abs_diff}")
print(f"translated_ms {statistics.median(elapsed):.17g}")
