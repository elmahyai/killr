import contextlib
import difflib
import io
import statistics
import time

from _mclust_dr_fit_fixture import PROOF, load_dr
from mclust.print_mclust_dr import print_MclustDR

dr = load_dr()


def one() -> str:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        print_MclustDR(dr)
    return out.getvalue()


# untimed call: printed text
value = one()
expected = (PROOF.parent / "docs/output/print.MclustDR-r.txt").read_text()
same = value == expected
print(f"matches {'true' if same else 'false'}")
print("max_abs_diff 0" if same else "max_abs_diff NaN (text differs)")
if not same:
    print("\n".join(difflib.unified_diff(expected.splitlines(), value.splitlines(), "R", "Python", lineterm="")))
(PROOF.parent / "docs/output/print.MclustDR-python.txt").write_text(value)

# timed: median of 20 calls of print() alone
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(f"translated_ms {statistics.median(elapsed):.17g}")
