import sys,time
sys.path.insert(0,"packages/blob")
from blob.blob import validate_blob
def f(): return validate_blob([b"abc",None]) is None
print(f());f();t=[]
for _ in range(20):
 a=time.perf_counter();f();t.append((time.perf_counter()-a)*1000)
print(f"translated_ms={sum(sorted(t)[9:11])/2:.9f}")
