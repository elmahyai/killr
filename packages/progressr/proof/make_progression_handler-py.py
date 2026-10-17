import json
import statistics
import time

from progressr.condition import progression, signal_condition, with_calling_handlers
from progressr.factory import make_progression_handler


def one():
    steps = []
    messages = []

    def update(config, state, progression, **_kwargs):
        steps.append(state["step"])
        messages.append(state["message"])

    handler = make_progression_handler(
        "rec",
        reporter={"update": update},
        enable=True,
        target="file",
        interval=0,
    )

    def go():
        signal_condition(
            progression(
                type="initiate",
                steps=4,
                auto_finish=True,
                progressor_uuid="p",
                progression_index=1,
            )
        )
        for index, text in enumerate(("a", "b", "c", "d"), start=2):
            signal_condition(
                progression(
                    type="update",
                    amount=1,
                    message=text,
                    progressor_uuid="p",
                    progression_index=index,
                )
            )

    with_calling_handlers(go, progression=handler)
    return {"steps": steps, "messages": messages}


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
value["median_ms"] = statistics.median(elapsed)
print(json.dumps(value))
