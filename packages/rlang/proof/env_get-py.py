import statistics
import time
from rlang import env, env_poke, env_get

def one():
    e = env(a=1)
    env_poke(e, "b", 2)
    return str(env_get(e, "b"))

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
