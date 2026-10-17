import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import describe, equals


def one():
    return equals([1, 2, 3], [1, 0, 3])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path('/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/equals-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('equals(c(1, 2), c(1, 0)) returns TRUE, FALSE.' + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
