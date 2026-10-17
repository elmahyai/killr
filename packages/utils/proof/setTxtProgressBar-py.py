import io
import statistics
import time

from utils import close, setTxtProgressBar, txtProgressBar


def one():
    buf = io.StringIO()
    bar = txtProgressBar(min=0, max=10, style=1, file=buf)
    value = setTxtProgressBar(bar, 4)
    close(bar)
    return value


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value)
print("%.17g" % statistics.median(elapsed))
