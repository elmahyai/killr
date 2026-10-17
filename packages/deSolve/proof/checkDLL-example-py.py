import sys
from types import ModuleType

ROOT = "/home/ahmed/killr_projects/killr"
sys.path.insert(0, f"{ROOT}/packages/deSolve")
if "deSolve" not in sys.modules:
    package = ModuleType("deSolve")
    package.__path__ = [f"{ROOT}/packages/deSolve/deSolve"]
    sys.modules["deSolve"] = package

from deSolve.checkDLL import NA_VALUE, NativeSymbol, checkDLL

sym = checkDLL(
    func="aquaphy",
    jacfunc=None,
    dllname="deSolve",
    initfunc="iniaqua",
    verbose=True,
    nout=6,
    outnames=[
        "PAR",
        "TotalN",
        "PhotoSynthesis",
        "NCratio",
        "ChlCratio",
        "Chlorophyll",
    ],
    JT=1,
)


def kind(value) -> str:
    if value is None:
        return "NULL"
    if value is NA_VALUE:
        return "NA"
    if isinstance(value, NativeSymbol):
        return "NativeSymbol"
    return type(value).__name__


colnames = sym.Nmtot["colnames"].values
print("class: deSolve.symbols")
print(f"ModelInit: {kind(sym.ModelInit)} ")
print(f"Func: {kind(sym.Func)} ")
print(f"JacFunc: {kind(sym.JacFunc)} ")
print(f"Nglobal: {sym.Nglobal} ")
print("colnames:", " ".join(colnames), "")
