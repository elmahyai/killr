import json
import os
import statistics
import tempfile
import time
import io
import contextlib

from cli import *
from cli._options import options
from cli.pluralize import _as_piece

options(**{'cli.num_colors': 8, 'cli.unicode': True})

def _abc_file():
    fd, path = tempfile.mkstemp()
    os.write(fd, b'abc')
    os.close(fd)
    return path

def one():
    
    return bg_br_red("Hello")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if isinstance(value, bool):
    shown = value
elif isinstance(value, int) and not isinstance(value, bool):
    shown = value
else:
    shown = value
if isinstance(value, bool):
    print("TRUE" if value else "FALSE")
elif isinstance(value, int) and not isinstance(value, bool):
    print(f"NUM {value}")
elif isinstance(value, float):
    print(f"NUM {value:.17g}")
else:
    data = "" if value is None else str(value)
    print("STR " + ",".join(str(byte) for byte in data.encode()))
print(f"MS {statistics.median(elapsed):.17g}")
