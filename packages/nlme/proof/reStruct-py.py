import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.restruct import fingerprint_restruct, load_pixel_csv, reStruct


def one():
    pixel = load_pixel_csv()
    rs1 = reStruct({"Dog": "~day", "Side": "~1"}, data=pixel)
    return fingerprint_restruct(rs1)


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
