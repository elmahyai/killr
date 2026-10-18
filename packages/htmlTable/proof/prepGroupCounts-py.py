import json, statistics, time, sys
sys.path.insert(0, "packages/htmlTable")
from htmlTable.html_table import prepGroupCounts
case = [1, 1, 2, 2, 2]
value = prepGroupCounts(case)
times = []
for _ in range(20):
    t = time.perf_counter(); prepGroupCounts(case); times.append((time.perf_counter()-t)*1000)
print(json.dumps({"value": value, "translated_ms": statistics.median(times)}))
