import statistics
import time
from quantreg import sfn_message

def one():
    return sfn_message(1).strip() + '|' + sfn_message(17).strip()
one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value = one()
print(value)
print(f'{statistics.median(elapsed):.17g}')
