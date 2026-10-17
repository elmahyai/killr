import json
import statistics
import time

from pbapply.dopb import dopb, replace_session_options, reset_session_options
from pbapply.startpb import replace_pboptions, reset_pboptions


def one():
    out = []
    out.append(float(dopb()))
    former = replace_pboptions(type="timer")
    try:
        out.append(float(dopb()))
    finally:
        reset_pboptions(former)
    former = replace_pboptions(type="none")
    try:
        out.append(float(dopb()))
    finally:
        reset_pboptions(former)
    former = replace_pboptions(type="txt")
    try:
        out.append(float(dopb()))
    finally:
        reset_pboptions(former)
    former = replace_pboptions(type="shiny")
    try:
        out.append(float(dopb()))
    finally:
        reset_pboptions(former)
    former = replace_pboptions(type=None)
    try:
        out.append(float(dopb()))
    finally:
        reset_pboptions(former)
    former = replace_pboptions(type="timer")
    knitr = replace_session_options(**{"knitr.in.progress": True})
    try:
        out.append(float(dopb()))
    finally:
        reset_session_options(knitr)
        reset_pboptions(former)
    former = replace_pboptions(type="tim")
    try:
        out.append(float(dopb()))
    finally:
        reset_pboptions(former)
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    json.dumps(
        {
            "value": value,
            "median_ms": statistics.median(elapsed),
        }
    )
)
