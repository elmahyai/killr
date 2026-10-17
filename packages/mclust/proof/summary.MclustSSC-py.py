import contextlib
import csv
import io
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.mclust_ssc import mclust_ssc
from mclust.print_mclust_ssc import print_summary_MclustSSC, summary_MclustSSC

PROOF = Path(__file__).parent


def _mod():
    import numpy as np

    x = np.loadtxt(PROOF / "MclustSSC_X.csv", delimiter=",", skiprows=1)
    with (PROOF / "MclustSSC_class.csv").open(newline="") as handle:
        cl = [
            float("nan") if row["class"] in ("", "NA") else row["class"]
            for row in csv.DictReader(handle)
        ]
    return mclust_ssc(x, cl, verbose=False)


def one():
    return summary_MclustSSC(_mod())


def rendered():
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        print_summary_MclustSSC(one())
    return out.getvalue()


value = one()
(PROOF.parent / "docs/output/summary.MclustSSC-python.txt").write_text(
    rendered()
)
expected = (PROOF.parent / "docs/output/summary.MclustSSC-r.txt").read_text()
print(f"matches {'true' if rendered() == expected else 'false'}")
print("max_abs_diff 0" if rendered() == expected else "max_abs_diff 1")
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(f"translated_ms {statistics.median(elapsed):.17g}")
