import json, statistics, time, sys
sys.path.insert(0, "packages/htmlTable")
from htmlTable.html_table import interactiveTable
case="<table><td>long text</td></table>"; value=interactiveTable(case); times=[]
for _ in range(20):
 t=time.perf_counter(); interactiveTable(case); times.append((time.perf_counter()-t)*1000)
print(json.dumps({"value":value,"translated_ms":statistics.median(times),
                  "runtime":"JavaScript not translated"}))
