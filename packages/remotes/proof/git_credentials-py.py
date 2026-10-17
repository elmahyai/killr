import json
import statistics
import time
from pathlib import Path

from remotes.git_credentials import git_credentials, options

out = Path(__file__).resolve().parents[1] / "docs" / "output" / "git_credentials-python.txt"
out.parent.mkdir(parents=True, exist_ok=True)

options.pop("remotes.git_credentials", None)
assert git_credentials() is None

options["remotes.git_credentials"] = "plain-token"


def one():
    return git_credentials()


value = one()
assert value == "plain-token"
out.write_text(
    'options["remotes.git_credentials"] = "plain-token"; git_credentials() returns '
    + value
    + ".\n",
    encoding="utf-8",
)

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
