import json
import statistics
import time

from progressr.condition import condition_message, progression


def one():
    condition = progression(message="hello", amount=2, type="update")
    return {
        "amount": condition["amount"],
        "type": condition["type"],
        "message": condition_message(condition),
        "class": list(condition.classes),
    }


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value["median_ms"] = statistics.median(elapsed)
print(json.dumps(value))
