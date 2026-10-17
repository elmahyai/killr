import json
import statistics
import sys
import time
from types import ModuleType

ROOT = "/home/ahmed/killr_projects/killr"
sys.path.insert(0, f"{ROOT}/packages/deSolve")
if "deSolve" not in sys.modules:
    package = ModuleType("deSolve")
    package.__path__ = [f"{ROOT}/packages/deSolve/deSolve"]
    sys.modules["deSolve"] = package

from deSolve.checkDLL import NativeSymbol, checkDLL


class Named(list):
    def __init__(self, values, names):
        super().__init__(values)
        self.names = list(names)


def _codes(text: str) -> list[float]:
    chars = [float(ord(ch)) for ch in text]
    return [float(len(chars)), *chars]


def pack(sym) -> list[float]:
    vals: list[float] = []
    nglobal = sym.Nglobal
    vals.append(-999.0 if nglobal is None else float(nglobal))
    vals.append(1.0 if isinstance(sym.ModelInit, NativeSymbol) else 0.0)
    vals.append(1.0 if isinstance(sym.Func, NativeSymbol) else 0.0)
    vals.append(0.0 if sym.JacFunc is None else 1.0)
    cols = sym.Nmtot.get("colnames")
    if cols is None:
        vals.append(-1.0)
    else:
        vals.append(0.0 if cols.mode == "character" else 1.0)
        vals.append(float(len(cols.values)))
        for index, value in enumerate(cols.values):
            name = "" if cols.names is None else cols.names[index]
            vals.extend(_codes(name))
            if cols.mode == "character":
                vals.extend(_codes("" if value is None else str(value)))
            else:
                vals.append(float(value))
    lengthvar = sym.Nmtot.get("lengthvar")
    if lengthvar is None:
        vals.append(0.0)
    else:
        vals.append(1.0)
        vals.append(float(len(lengthvar.values)))
        for index, value in enumerate(lengthvar.values):
            vals.append(-1.0 if value is None else float(value))
            name = "" if lengthvar.names is None else lengthvar.names[index]
            vals.extend(_codes(name))
    return vals


def one() -> list[float]:
    out6 = [
        "PAR",
        "TotalN",
        "PhotoSynthesis",
        "NCratio",
        "ChlCratio",
        "Chlorophyll",
    ]
    parts = [
        checkDLL("aquaphy", None, "deSolve", "iniaqua", True, 6, out6, 1),
        checkDLL(
            "aquaphy",
            "iniaqua",
            "deSolve",
            None,
            True,
            4,
            ["PAR", "PAR", "TotalN", "PhotoSynthesis", "Extra"],
            1,
        ),
        checkDLL("aquaphy", None, "deSolve", "deSolve", False, 4, ["A", "B"], 1),
        checkDLL("aquaphy", None, "deSolve", None, False, 3, [1, 2], 1),
        checkDLL("aquaphy", None, "deSolve", None, False, 0, ["A"], 1),
        checkDLL(
            "aquaphy",
            None,
            "deSolve",
            "iniaqua",
            False,
            2,
            Named(["x", "x", "y"], ["A", "B", "C"]),
            1,
        ),
        checkDLL("aquaphy", None, "deSolve", None, False, 0, [], 1),
    ]
    fa = checkDLL("aquaphy", None, "deSolve", None, False, 0, None, 1)
    fb = checkDLL("aquaphyforc", None, "deSolve", None, False, 0, None, 1)
    fc = checkDLL("iniaqua", None, "deSolve", None, False, 0, None, 1)
    value: list[float] = []
    for item in parts:
        value.extend(pack(item))
    value.extend(pack(fa))
    value.extend(pack(fb))
    value.extend(pack(fc))
    value.append(1.0 if fa.Func.address == fb.Func.address else 0.0)
    value.append(1.0 if fa.Func.address == fc.Func.address else 0.0)
    return value


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
