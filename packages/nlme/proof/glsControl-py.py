import statistics
import sys
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if "nlme" not in sys.modules:
    _pkg = types.ModuleType("nlme")
    _pkg.__path__ = [str(ROOT / "nlme")]
    sys.modules["nlme"] = _pkg
from nlme.glscontrol import glsControl


def vals(x):
    return [
        x["maxIter"],
        x["msMaxIter"],
        x["tolerance"],
        x["msTol"],
        float(x["msVerbose"]),
        float(x["singular.ok"]),
        float(x["returnObject"]),
        float(x["apVar"]),
        x["minAbsParApVar"],
        x[".relStep"],
        float(x["opt"] == "nlminb"),
        float(x["optimMethod"] == "BFGS"),
        float(x["natural"]),
        x["sigma"],
    ]


def one():
    a = glsControl()
    b = glsControl(
        maxIter=10,
        msMaxIter=20,
        tolerance=1e-4,
        msTol=1e-5,
        msVerbose=True,
        singular_ok=True,
        returnObject=True,
        apVar=False,
        minAbsParApVar=0.1,
        opt="optim",
        optimMethod="Nelder-Mead",
        natural=False,
        sigma=2,
        relStep=0.01,
    )
    return vals(a) + vals(b)


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
