import io
import json
import statistics
import time
from contextlib import redirect_stdout
from pathlib import Path

from magrittr.fseq import debug_pipe

out = Path(__file__).resolve().parents[1] / "docs" / "output"
out.mkdir(parents=True, exist_ok=True)


def one():
    return debug_pipe(5)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))

captured = io.StringIO()
with redirect_stdout(captured):
    result = debug_pipe(5)
(out / "debug_pipe-python.txt").write_text(
    captured.getvalue() + f"debug_pipe(5) returns {result}.\n"
)
