import json
import statistics
import time
from pathlib import Path

from stringi._na import NA


def plain(value):
    if value is NA:
        return None
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value



from stringi.sprintf import stri_printf

path = Path("/tmp/stringi-rest-proof/printf-py.txt")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_bytes(b"")
stri_printf("%s", ["a", "b"], file=str(path))
shown = ", ".join(str(item) for item in path.read_bytes())
Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_printf-python.txt").write_text(
    f"stri_printf('%s', ['a', 'b']) writes {shown}.\n"
)


def one():
    stri_printf("%s", ["a", "b"], file=str(path))
    return None


one()
value = list(path.read_bytes())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
