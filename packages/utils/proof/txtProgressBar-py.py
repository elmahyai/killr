import io
import statistics
import time

from utils import close, setTxtProgressBar, txtProgressBar


def one():
    buf = io.StringIO()
    bar = txtProgressBar(min=0, max=10, style=3, file=buf)
    setTxtProgressBar(bar, 5)
    close(bar)
    return buf.getvalue()


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("%.17g" % statistics.median(elapsed))
