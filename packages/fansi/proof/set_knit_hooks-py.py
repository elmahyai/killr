import contextlib
import io
import json
import statistics
import time
from fansi.set_knit_hooks import set_knit_hooks

def one():
    class Hooks:
        def get(self, name):
            return lambda x, options: "old-output"
        def set(self, **kwargs):
            return None
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        old = set_knit_hooks(Hooks())
    style = buf.getvalue().rstrip("\n")
    return style + "\n" + old["output"]("z", None)

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = [value] if isinstance(value, str) else value
print(json.dumps({"value": [item.encode("utf-8").hex() if isinstance(item, str) else "null" for item in shown], "median_ms": statistics.median(elapsed)}))
