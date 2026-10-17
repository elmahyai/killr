import sys
import time

sys.path.insert(0, "packages/xmlparsedata")
from xmlparsedata._api import xml_parse_data

pd = [
    {"line1": 1, "col1": 1, "line2": 1, "col2": 5, "id": 5, "parent": 0,
     "token": "expr", "terminal": False, "text": ""},
    {"line1": 1, "col1": 1, "line2": 1, "col2": 1, "id": 1, "parent": 5,
     "token": "SYMBOL", "terminal": True, "text": "x"},
    {"line1": 1, "col1": 3, "line2": 1, "col2": 3, "id": 2, "parent": 5,
     "token": "'+'", "terminal": True, "text": "+"},
    {"line1": 1, "col1": 5, "line2": 1, "col2": 5, "id": 3, "parent": 5,
     "token": "NUM_CONST", "terminal": True, "text": "1"},
    {"line1": 1, "col1": 5, "line2": 1, "col2": 5, "id": 4, "parent": 3,
     "token": "expr", "terminal": False, "text": ""},
]
out = xml_parse_data(pd)
with open("packages/xmlparsedata/docs/output/xml_parse_data-py.txt", "w") as f:
    f.write(out + "\n")
xml_parse_data(pd)
times = []
for _ in range(20):
    t0 = time.perf_counter()
    xml_parse_data(pd)
    times.append((time.perf_counter() - t0) * 1000)
print(f"translated_ms={sorted(times)[9]:.9f}")
