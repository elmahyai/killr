import sys, time
sys.path.insert(0, "packages/blob")
from blob.blob import as_blob
def f(): return as_blob(["abc", None])
v = f()
print(";".join(",".join(map(str, z)) if z is not None else "NA" for z in v))
f()
times = []
for _ in range(20):
    start = time.perf_counter(); f(); times.append((time.perf_counter()-start)*1000)
print(f"translated_ms={sorted(times)[9:11][0] if len(times)%2 else sum(sorted(times)[9:11])/2:.9f}")
