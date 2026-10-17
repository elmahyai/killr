import importlib.util
import json
import statistics
import sys
import tempfile
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT)]


def _load_submodule(name: str, path: Path, package: str = "e1071"):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = package
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


if "e1071" not in sys.modules:
    sys.modules["e1071"] = types.ModuleType("e1071")

write_mod = _load_submodule(
    "e1071.write_matrix_csr",
    ROOT / "e1071" / "write_matrix_csr.py",
)
read_mod = _load_submodule(
    "e1071.read_matrix_csr",
    ROOT / "e1071" / "read_matrix_csr.py",
)
write_matrix_csr = write_mod.write_matrix_csr
read_matrix_csr = read_mod.read_matrix_csr
matrix_csr_as_numeric = read_mod.matrix_csr_as_numeric


def one():
    matrix = [[1, 0, 3, 0], [2, 0, 4, 0]]
    y = ["A", "B"]
    path = Path(tempfile.mkstemp(suffix=".dat")[1])
    write_matrix_csr(matrix, str(path), y=y, fac=True)
    out = read_matrix_csr(str(path), fac=True)
    return matrix_csr_as_numeric(out["x"])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
