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



from stringi.files import stri_read_lines

path = Path("/tmp/stringi-rest-proof/read-py-lines.txt")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_bytes("café\nNA\n\n".encode())
Path("/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_read_lines-python.txt").write_text(
    f"stri_read_lines(path) returns {len(stri_read_lines(str(path)))} lines.\n"
)


def one():
    return stri_read_lines(str(path))

value = plain(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
