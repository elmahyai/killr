import json, statistics, time, sys
sys.path.insert(0, "packages/htmlTable")
from htmlTable.html_table import vector2string
case = ["a", "b'b", "c"]; value = vector2string(case); times = []
for _ in range(20):
    t=time.perf_counter(); vector2string(case); times.append((time.perf_counter()-t)*1000)
print(json.dumps({"value":value, "translated_ms":statistics.median(times)}))
