import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.gnlscontrol import gnlsControl


def one():
    x = gnlsControl()
    return [
        x["maxIter"],
        x["nlsMaxIter"],
        x["msMaxIter"],
        x["minScale"],
        x["tolerance"],
        x["nlsTol"],
        x["msTol"],
        float(x["returnObject"]),
        float(x["msVerbose"]),
        float(x["apVar"]),
        0.0 if x["opt"] == "nlminb" else 1.0,
        x[".relStep"],
        x["minAbsParApVar"],
        x["sigma"],
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
