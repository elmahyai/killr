import json
import statistics
import time
from xml2 import *
def print_value(value):
    if value is None:
        return 'NA'
    if isinstance(value, bool):
        return 'TRUE' if value else 'FALSE'
    if isinstance(value, float) and value == int(value):
        return str(int(value)) if abs(value) < 1e15 else str(value)
    if isinstance(value, list):
        return ' '.join(print_value(item) for item in value)
    return str(value)
def _capture(fn):
    import contextlib, io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn()
    return buf.getvalue().rstrip('\n')
def one():
    x = read_xml("<a id='1'/>")
    xml_set_attrs(x, {"b": "two"})
    return as_character(x)
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = value
if shown is None:
    shown = None
print(json.dumps({'value': shown, 'median_ms': statistics.median(elapsed)}))
