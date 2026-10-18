import json, statistics, time
from labelled import LabelledVector, is_user_na
x = LabelledVector([1, 9, None], na_values=[9])
value = is_user_na(x); t = []
for _ in range(20):
    s=time.perf_counter(); is_user_na(x); t.append((time.perf_counter()-s)*1000)
print(json.dumps({"value": value, "median_ms": statistics.median(t)}))
