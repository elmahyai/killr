import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/xtable")

from xtable.ftable_print import Ftable, as_is, as_math, xtable_ftable
from xtable.sanitize_final import sanitize_final
from xtable.string_connection import StringConnection


def one():
    s = StringConnection('a  align="left"  b')
    z = xtable_ftable(
        Ftable([["A", "1"]], row_vars=["row"], col_vars=["col"]),
        caption="Cap", label="tab:x",
    )
    return {
        "sanitize_final": sanitize_final(s, type="html").text,
        "as_is": as_is(["a", "b"]),
        "as_math": as_math("x"),
        "ftable": [
            z.attrs["ftableCaption"], z.attrs["ftableLabel"],
            z.attrs["method"], *(str(v) for v in z.attrs["nChars"]),
        ],
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
