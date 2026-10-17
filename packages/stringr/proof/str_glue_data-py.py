import json
import statistics
import time
from pathlib import Path

from stringr.glue import str_glue_data

out_dir = Path(__file__).resolve().parents[1] / "docs" / "output"
out_dir.mkdir(parents=True, exist_ok=True)
rows = str_glue_data(
    {"name": ["Mazda RX4", "Datsun 710"], "hp": [110, 93]},
    "{name} has {hp} hp",
)
(out_dir / "str_glue_data-python.txt").write_text("\n".join(rows) + "\n")


def one():
    return str_glue_data(
        {"name": ["Mazda RX4", "Datsun 710"], "hp": [110, 93]},
        "{name} has {hp} hp",
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
