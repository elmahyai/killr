import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import describe, nest_pas


def one():
    return nest_pas([True, False, True])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path("/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/n'est pas-python.txt")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("n'est pas(c(FALSE, TRUE)) returns TRUE, FALSE." + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
