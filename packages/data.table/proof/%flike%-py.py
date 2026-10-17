import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/data.table")
from datatable import *


def flat(value):
    import math
    def one(item):
        if item is None:
            return 'NA'
        if isinstance(item, bool):
            return 'TRUE' if item else 'FALSE'
        if isinstance(item, str):
            return item
        if isinstance(item, float):
            return 'NaN' if math.isnan(item) else format(item, '.16g')
        return str(item)
    if value is None:
        return 'null'
    if isinstance(value, list):
        if not value:
            return ''
        if any(isinstance(item, list) for item in value):
            return '/'.join(flat(item) for item in value)
        return '|'.join(one(item) for item in value)
    return one(value)


def one():
    return flike(['a.b', 'axb'], 'a.b')


value = flat(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({'value': value, 'median_ms': statistics.median(elapsed)}))
