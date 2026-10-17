import io
import json
import statistics
import time

from utf8 import (
    as_utf8,
    output_ansi,
    output_utf8,
    utf8_encode,
    utf8_format,
    utf8_normalize,
    utf8_print,
    utf8_valid,
    utf8_width,
)
def one():
    return utf8_encode("hello\nworld")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}, ensure_ascii=False))
