import json
import statistics
import time
from sqlalchemy import create_engine, text
from withr import with_db_connection


def one():
    engine = create_engine("sqlite:///:memory:")
    con = engine.connect()
    con.execute(text("CREATE TABLE t (x REAL)"))
    con.execute(text("INSERT INTO t VALUES (1), (2)"))
    total = with_db_connection(
        {"con": con},
        lambda con: con.execute(text("SELECT SUM(x) FROM t")).scalar_one(),
    )
    closed = con.closed
    engine.dispose()
    return [total, closed]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
