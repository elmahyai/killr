import json
import os
import statistics
import time

from remotes.gitlab_pat import gitlab_pat

os.environ["GITLAB_PAT"] = "glpat-example"


def one():
    return gitlab_pat()


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

os.environ["GITLAB_PAT"] = ""
if gitlab_pat() is not None:
    raise SystemExit("empty GITLAB_PAT should return None")
del os.environ["GITLAB_PAT"]
if gitlab_pat() is not None:
    raise SystemExit("unset GITLAB_PAT should return None")

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
