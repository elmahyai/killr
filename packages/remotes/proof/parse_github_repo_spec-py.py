import json
import statistics
import time

from remotes.parse import parse_github_repo_spec


def one():
    return parse_github_repo_spec("igraph=igraph/rigraph")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
