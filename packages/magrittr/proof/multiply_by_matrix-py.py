import json
import statistics
import time
from pathlib import Path

from magrittr.aliases import Matrix, describe, multiply_by_matrix


def one():
    return multiply_by_matrix(Matrix([1, 2, 3, 4, 5, 6], nrow=2), Matrix([1, 2, 3, 4, 5, 6], nrow=3))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = Path('/home/ahmed/killr_projects/killr/packages/magrittr/docs/output/multiply_by_matrix-python.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('multiply_by_matrix(matrix(1:6, 2, 3), matrix(1:6, 3, 2)) returns 22, 49, 28, 64.' + "\n")
payload = describe(value)
payload["median_ms"] = statistics.median(elapsed)
print(json.dumps(payload))
