import importlib.util
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "write_matrix_csr",
    ROOT / "e1071" / "write_matrix_csr.py",
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)
write_matrix_csr = _mod.write_matrix_csr


def one():
    matrix = [[1, 0, 3, 0], [2, 0, 4, 0]]
    y = ["A", "B"]
    path = Path(tempfile.mkstemp(suffix=".dat")[1])
    write_matrix_csr(matrix, str(path), y=y, fac=True)
    return path.read_text(encoding="utf-8").rstrip("\n")


text = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"text": text, "median_ms": statistics.median(elapsed)}))
