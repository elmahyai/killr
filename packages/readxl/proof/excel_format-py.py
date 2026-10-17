import statistics
import sys
import time

from readxl import excel_format, readxl_example
def one():
    files = ["a.xlsx", "b.xls", "c.png", "/etc/hostname", readxl_example("clippy.xlsx"), readxl_example("deaths.xls")]
    return "|".join("NA" if item is None else item for item in excel_format(files))

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
