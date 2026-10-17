import json
import statistics
import time

from progressr.condition import condition_message
from progressr.evaluate import with_progress
from progressr.factory import make_progression_handler
from progressr.progressor import progressor


def _record(config, state, progression):
    return {
        "type": progression["type"],
        "amount": progression["amount"],
        "message": condition_message(progression),
        "step": state["step"],
        "max_steps": config["max_steps"],
    }


def one():
    seen = []
    handler = make_progression_handler(
        "rec",
        reporter={
            "initiate": lambda config, state, progression, **_kwargs: seen.append(
                _record(config, state, progression)
            ),
            "update": lambda config, state, progression, **_kwargs: seen.append(
                _record(config, state, progression)
            ),
        },
        enable=True,
        target="file",
        interval=0,
    )

    def body():
        progress = progressor(along=range(1, 6))
        total = 0
        for value in range(1, 6):
            total += value
            progress(message=str(value))
        return total

    total = with_progress(
        body,
        handlers=handler,
        enable=True,
        interval=0,
        delay_terminal=False,
        delay_stdout=False,
        delay_conditions=(),
    )
    return {"sum": total, "events": seen}


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value["median_ms"] = statistics.median(elapsed)
print(json.dumps(value))
