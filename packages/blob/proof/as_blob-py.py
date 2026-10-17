import sys, time
sys.path.insert(0, "packages/blob")
from blob.blob import as_blob
def f(): return as_blob(["abc", None])
v = f()
print(";".join(",".join(map(str, z)) if z is not None else "NA" for z in v))
f(); times = []
for _ in range(20):
    a = time.perf_counter(); f(); times.append((time.perf_counter()-a)*1000)
print(f"translated_ms={sorted(times)[9:11] and sum(sorted(times)[9:11])/2:.9f}")
