import statistics
import sys
import time

from readxl import format_from_signature, readxl_example
def one():
    files = [readxl_example("clippy.xlsx"), readxl_example("deaths.xls")]
    return "|".join(format_from_signature(files))

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
