import sys, time
sys.path.insert(0, "packages/blob")
from blob.blob import blob
def f(): return blob(b"abc", None)
v = f(); print(";".join(",".join(map(str, z)) if z is not None else "NA" for z in v))
f(); t = []
for _ in range(20):
    a=time.perf_counter(); f(); t.append((time.perf_counter()-a)*1000)
print(f"translated_ms={sum(sorted(t)[9:11])/2:.9f}")
