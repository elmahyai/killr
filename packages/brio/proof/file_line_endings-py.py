import json, statistics, tempfile, time, sys
sys.path.insert(0, str(__file__).split("/packages/")[0] + "/packages/brio")
from brio import file_line_endings
with tempfile.NamedTemporaryFile() as f:
    f.write(b"a\r\nb\n"); f.flush()
    one = lambda: file_line_endings(f.name)
    value = one(); times = []
    for _ in range(20):
        t = time.perf_counter(); one(); times.append((time.perf_counter()-t)*1000)
    print(json.dumps({"value": value, "median_ms": statistics.median(times)}))
