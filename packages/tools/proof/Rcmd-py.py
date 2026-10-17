import statistics
import time

def one():
    from tools.rcmd import rcmd
    s1 = rcmd(["config", "CC"])
    s2 = rcmd(["config", "NOT_A_VAR"])
    return f"S {s1} {s2}\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
