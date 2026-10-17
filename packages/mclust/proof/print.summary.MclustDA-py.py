import contextlib
import io
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.print_summary_mclust_da import print_summary_MclustDA

PROOF = Path(__file__).parent


def make_summary():
    return {
        "type": "EDDA",
        "n": np.array([2, 2]),
        "d": 2,
        "loglik": -12.5,
        "df": 8,
        "bic": 1.25,
        "nclass": 2,
        "classes": ["A", "B"],
        "G": np.array([1, 1]),
        "modelName": ["EII", "EII"],
        "prop": {"A": 0.5, "B": 0.5},
        "tab": {
            "values": np.array([[2, 0], [0, 2]]),
            "dimnames": {"Classes": ["A", "B"], "Predicted": ["A", "B"]},
        },
        "ce": 0.0,
        "brier": 0.0008186628291109271,
        "tab.newdata": None,
        "ce.newdata": None,
        "brier.newdata": None,
        "printParameters": False,
    }


def rendered():
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        print_summary_MclustDA(make_summary())
    return output.getvalue()


value = rendered()
(PROOF.parent / "docs/output/print.summary.MclustDA-python.txt").write_text(value)
expected = (PROOF.parent / "docs/output/print.summary.MclustDA-r.txt").read_text()
matches = value == expected
print(f"matches {'true' if matches else 'false'}")
print(f"max_abs_diff {0 if matches else 1}")
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    rendered()
    elapsed.append((time.perf_counter() - started) * 1000)
translated_ms = statistics.median(elapsed)
print(f"translated_ms {translated_ms:.17g}")
print(f"r_ms unavailable")
