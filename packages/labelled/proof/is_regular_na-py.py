import json, statistics, time
from labelled import LabelledVector, TaggedNA, is_regular_na
x = LabelledVector([1, None, 9, TaggedNA("a")], na_values=[9])
value = is_regular_na(x)
times = []
for _ in range(20):
    t = time.perf_counter(); is_regular_na(x); times.append((time.perf_counter()-t)*1000)
print(json.dumps({"value": value, "median_ms": statistics.median(times)}))
