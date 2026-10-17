import statistics
import time
from curl import file_writer

def one():
    import tempfile
    handle = tempfile.NamedTemporaryFile(delete=False)
    handle.close()
    writer = file_writer(handle.name)
    writer(b"Hello!\n")
    writer(b"ok\n", close=True)
    return "|".join(open(handle.name).read().splitlines())

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if isinstance(value, bool):
    shown = "TRUE" if value else "FALSE"
elif value is None:
    shown = "NULL"
else:
    shown = str(value).replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
