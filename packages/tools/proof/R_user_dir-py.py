import statistics
import time

def one():
    from tools.session import R_user_dir
    return R_user_dir("tools", "data") + "|" + R_user_dir("tools", "config") + "|" + R_user_dir("tools", "cache") + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
