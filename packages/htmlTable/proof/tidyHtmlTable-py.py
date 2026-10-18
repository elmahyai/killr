import json, statistics, time, sys
sys.path.insert(0, "packages/htmlTable")
from htmlTable.html_table import tidyHtmlTable
case={"name":["a"],"value":[1]}; value=tidyHtmlTable(case); times=[]
for _ in range(20):
 t=time.perf_counter(); tidyHtmlTable(case); times.append((time.perf_counter()-t)*1000)
print(json.dumps({"value":value,"translated_ms":statistics.median(times),
                  "waiting":"checkmate, htmlwidgets for package installation"}))
