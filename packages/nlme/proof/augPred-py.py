import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlme.augpred import augPred
from nlme.augpred_fixtures import orthodont_fixtures

FIXTURES = orthodont_fixtures()


def one():
    return augPred(FIXTURES.fm2, length_out=5).flatten_numeric()


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (",".join("%.17g" % float(part) for part in value), statistics.median(elapsed))
)
