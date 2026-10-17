import statistics
import time

def one():
    from tools.concordance import match_concordance
    con = {"offset": 0, "srcFile": "a.Rnw", "srcLine": [1, 2, 4]}
    rows = match_concordance([1, 2, 3], con)
    return "|".join(f"{a}:{b}" for a, b in rows) + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
