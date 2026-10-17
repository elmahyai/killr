import statistics
import time

def one():
    from tools.htmlheader import html_header
    return "\n".join(html_header("Hello", logo=False, up=None, top=None, rhome="")) + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
