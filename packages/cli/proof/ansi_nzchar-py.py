import contextlib
import io
import statistics
import time

from cli import *
from cli._options import options

options(**{"cli.num_colors": 8, "cli.unicode": True})

def _quiet(fn):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        value = fn()
    return value

def one():
    return "|".join("TRUE" if item else "FALSE" for item in ansi_nzchar(["", col_red("x")]))

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if value is None:
    print('NULL')
elif isinstance(value, bool):
    print('TRUE' if value else 'FALSE')
elif isinstance(value, int) and not isinstance(value, bool):
    print(f'NUM {value}')
elif isinstance(value, float):
    print(f'NUM {value:.17g}')
else:
    data = '' if value is None else str(value)
    print('STR ' + ','.join(str(byte) for byte in data.encode()))
print(f'MS {statistics.median(elapsed):.17g}')
