import statistics
import time

def one():
    from tools.concordance import follow_concordance
    con = {"offset": 0, "srcFile": "a.Rnw", "srcLine": [1, 2, 4]}
    prev = {"offset": 0, "srcFile": "a.R", "srcLine": [10, None, 30, 40]}
    got = follow_concordance(con, prev)
    return ",".join(got["srcFile"]) + " " + ",".join(str(v) for v in got["srcLine"]) + "\n"

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(value, end="")
print("MS")
print(f"{statistics.median(elapsed):.17g}")
