import json
import statistics
import time
import os
from fansi import dflt_css, dflt_term_cap, fansi_lines, fansi_unicode_version, fwl, html_code_block, in_html, sgr_256, term_cap_test

def one():
    return fansi_unicode_version()

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
