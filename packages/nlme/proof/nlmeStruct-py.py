import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.corar1 import coef, corAR1
from nlme.nlmestruct import nlmeStruct
from nlme.restruct import load_pixel_csv, reStruct


def one():
    pixel = load_pixel_csv()
    rs = reStruct({"Dog": "~day", "Side": "~1"}, data=pixel)
    ns = nlmeStruct(reStruct=rs, corStruct=corAR1(0.3, form="~1 | Dog"))
    ns2 = nlmeStruct(reStruct=rs)
    return [
        len(ns), len(ns2), len(nlmeStruct(reStruct=None)), len(ns.classes),
        *[float(v) for v in ns.settings],
        *[float(v) for v in coef(ns["corStruct"], unconstrained=True).values],
        len(ns["reStruct"]),
        *[float(v) for v in ns2.settings],
        float("corStruct" not in ns2.components),
        float("reStruct" not in nlmeStruct(reStruct=None).components),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (",".join("%.17g" % float(part) for part in value), statistics.median(elapsed))
)
