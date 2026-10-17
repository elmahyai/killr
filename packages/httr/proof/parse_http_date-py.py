import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/httr")

from httr.date import Character, Date, POSIXct, parse_http_date


class Named(list):
    def __init__(self, values, names):
        super().__init__(values)
        self.names = names


def fmt_num(value):
    if value is None:
        return "NA"
    return format(value, ".17g")


def show(value):
    if value is None:
        return "NULL"
    if isinstance(value, POSIXct):
        vals = ",".join(fmt_num(item) for item in value.seconds)
        names = "" if not value.names else ",".join(value.names)
        return f"POSIXct[{vals}] tz={value.tz} names={names}"
    if isinstance(value, Date):
        vals = ",".join(fmt_num(item) for item in value.days)
        return f"Date[{vals}]"
    if isinstance(value, Character):
        body = " | ".join("NA" if item is None else item for item in value.values)
        names = "" if not value.names else ",".join(value.names)
        return f"chr[{body}] names={names}"
    return "OTHER " + type(value).__name__


def one():
    failure2 = Date([None, 3])
    named = Named(
        ["Sun, 06 Nov 1994 08:49:37 GMT", "Mon, 07 Nov 1994 00:00:00 GMT"],
        ["a", "b"],
    )
    lines = [
        show(parse_http_date("Sun, 06 Nov 1994 08:49:37 GMT")),
        show(parse_http_date("Sunday, 06-Nov-94 08:49:37 GMT")),
        show(parse_http_date("Sun Nov  6 08:49:37 1994")),
        show(parse_http_date(["Sun, 06 Nov 1994 08:49:37 GMT", "Mon, 07 Nov 1994 00:00:00 GMT"])),
        show(parse_http_date(["Sun, 06 Nov 1994 08:49:37 GMT", "Sunday, 06-Nov-94 08:49:37 GMT"])),
        show(parse_http_date("not a date")),
        show(parse_http_date(["Sun, 06 Nov 1994 08:49:37 GMT", None])),
        show(parse_http_date("")),
        show(parse_http_date([])),
        show(parse_http_date(None)),
        show(parse_http_date("nope", failure="bad")),
        show(parse_http_date(["nope", "x"], failure=failure2)),
        show(parse_http_date("Monday, 06 Nov 1994 08:49:37 GMT")),
        show(parse_http_date("sun, 06 nov 1994 08:49:37 gmt")),
        show(parse_http_date("SUN, 06 NOVEMBER 1994 08:49:37 GMT")),
        show(parse_http_date("Sun, 6 Nov 1994 8:9:7 GMT")),
        show(parse_http_date("Sun,  06 Nov 1994 08:49:37 GMT")),
        show(parse_http_date("Sun,06Nov1994 08:49:37 GMT")),
        show(parse_http_date("Sun, 06 Nov 1994 08:49:37 GMT extra")),
        show(parse_http_date(" Sun, 06 Nov 1994 08:49:37 GMT")),
        show(parse_http_date("Monday, 01-Jan-68 00:00:00 GMT")),
        show(parse_http_date("Thursday, 01-Jan-69 00:00:00 GMT")),
        show(parse_http_date("Saturday, 01-Jan-00 00:00:00 GMT")),
        show(parse_http_date("Sunday, 06-Nov-4 08:49:37 GMT")),
        show(parse_http_date("Sun, 06 Nov 1994 24:00:00 GMT")),
        show(parse_http_date("Sun, 06 Nov 1994 24:01:00 GMT")),
        show(parse_http_date("Sun, 06 Nov 1994 08:59:60 GMT")),
        show(parse_http_date("Sun, 06 Nov 1994 23:59:60 GMT")),
        show(parse_http_date("Sun, 06 Nov 1994 08:49:61 GMT")),
        show(parse_http_date("Tue, 29 Feb 2000 00:00:00 GMT")),
        show(parse_http_date("Thu, 29 Feb 1900 00:00:00 GMT")),
        show(parse_http_date("Sun, 31 Apr 1994 00:00:00 GMT")),
        show(parse_http_date("Mon, 31 Jan 1994 24:00:00 GMT")),
        show(parse_http_date("Sat, 31 Dec 1994 24:00:00 GMT")),
        show(parse_http_date("Sun Nov  6 08:49:37 19945")),
        show(parse_http_date("Sun, 06 Nov 999 08:49:37 GMT")),
        show(parse_http_date("Sun, 06 Nov 0 00:00:00 GMT")),
        show(parse_http_date("Wed, 31 Dec 1969 23:59:59 GMT")),
        show(parse_http_date(1)),
        show(parse_http_date(named)),
        show(parse_http_date("nope", failure=None)),
    ]
    return "\n".join(lines)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
