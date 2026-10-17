import importlib.util
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
_module_path = Path(__file__).resolve().parent.parent / "mclust" / "unmap_util.py"
_spec = importlib.util.spec_from_file_location("unmap_util", _module_path)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
unmap = _mod.unmap


def one():
    return unmap([1, 2, 1, 3, 2]).ravel(order="F")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
