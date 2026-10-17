import statistics
import sys
import time

from readxl import cell_limits
def one():
    return str(cell_limits([None, 7], [3, None]))

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
sys.stdout.write("VALUE\n")
sys.stdout.write(value)
sys.stdout.write("\n<<<END>>>\n")
sys.stdout.write(f"MS {statistics.median(elapsed):.17g}\n")
