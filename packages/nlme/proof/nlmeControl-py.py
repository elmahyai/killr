import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.nlmecontrol import nlmeControl


def one():
    x = nlmeControl()
    y = nlmeControl(maxIter=100, opt="nlm", sigma=2, extraOpt=3)
    return [
        x["maxIter"], x["pnlsMaxIter"], x["msMaxIter"], x["minScale"], x["tolerance"], x["niterEM"],
        x["pnlsTol"], x["msTol"], float(x["returnObject"]), float(x["msVerbose"]),
        float(x["msWarnNoConv"]), float(x["gradHess"]), float(x["apVar"]),
        x[".relStep"], x["minAbsParApVar"], 0.0 if x["opt"] == "nlminb" else 1.0,
        float(x["natural"]), x["sigma"],
        y["maxIter"], 1.0 if y["opt"] == "nlm" else 0.0, y["sigma"], y["extraOpt"],
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
