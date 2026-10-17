import sys
import time

sys.path.insert(0, "packages/xmlparsedata")
from xmlparsedata._api import xml_parse_token_map

with open("packages/xmlparsedata/docs/output/xml_parse_token_map-py.txt", "w") as f:
    f.write("\n".join(f"{key}\t{value}" for key, value in xml_parse_token_map.items()) + "\n")
xml_parse_token_map
times = []
for _ in range(20):
    t0 = time.perf_counter()
    _ = xml_parse_token_map
    times.append((time.perf_counter() - t0) * 1000)
print(f"translated_ms={sorted(times)[9]:.9f}")
