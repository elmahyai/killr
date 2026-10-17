import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import Matrix, describe, set_rownames


def one():
    return set_rownames(Matrix(list(range(1, 7)), nrow=2), ["u", "v"])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path('/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/set_rownames-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('set_rownames(matrix(1:4, 2, 2), c(u, v)) returns rows u and v.' + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
