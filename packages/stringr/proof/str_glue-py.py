import json
import statistics
import time
from pathlib import Path

from stringr.glue import str_glue

out_dir = Path(__file__).resolve().parents[1] / "docs" / "output"
out_dir.mkdir(parents=True, exist_ok=True)
name = "Fred"
age = 50
anniversary = "Saturday, October 12, 1991"
lines = str_glue(
    "My name is {name}, ",
    "my age next year is {age + 1}, ",
    "and my anniversary is {anniversary}.",
) + str_glue("My name is {name}, not {{name}}.")
(out_dir / "str_glue-python.txt").write_text("\n".join(lines) + "\n")


def one():
    name = "Fred"
    age = 50
    anniversary = "Saturday, October 12, 1991"
    return str_glue(
        "My name is {name}, ",
        "my age next year is {age + 1}, ",
        "and my anniversary is {anniversary}.",
    ) + str_glue("My name is {name}, not {{name}}.")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
