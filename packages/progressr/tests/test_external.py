"""External handlers stop at the missing suggested package."""

import pytest

from progressr.evaluate import with_progress
from progressr.external import (
    handler_beepr,
    handler_brrr,
    handler_notifier,
    handler_ntfy,
    handler_pbmcapply,
    handler_rpushbullet,
    handler_rstudio,
    handler_shiny,
    progress_progressr,
    with_progress_shiny,
)
from progressr.factory import make_progression_handler
from progressr.options import ProgressrError
from progressr.progressor import progressor


_BEEPR = "there is no package called \u2018beepr\u2019"
_BRRR = (
    "Package 'BRRR' is not available. "
    "See ?progressr::handler_notifier() for installation instructions"
)
_NOTIFIER = (
    "Package 'notifier' is not available. "
    "See ?progressr::handler_notifier() for installation instructions"
)
_NTFY = (
    "Package 'ntfy' is not available. "
    "See ?progressr::handler_ntfy() for installation instructions"
)
_PBMCAPPLY = "there is no package called \u2018pbmcapply\u2019"
_RPUSHBULLET = "Package RPushbullet is not available"
_RSTUDIO = "there is no package called \u2018rstudioapi\u2019"
_SHINY = "there is no package called \u2018shiny\u2019"

_EVENTS = [
    ("initiate", 1.0),
    ("update", 1.0),
    ("update", 1.0),
    ("finish", 1.0),
    ("finish", 1.0),
]


def _message(call):
    with pytest.raises(ProgressrError) as caught:
        call()
    return str(caught.value)


def _two_steps(handler):
    def body():
        progress = progressor(steps=2, on_exit=False)
        progress()
        progress()

    return with_progress(
        body,
        handlers=handler,
        enable=True,
        interval=0,
        delay_terminal=False,
        delay_stdout=False,
        delay_conditions=(),
    )


def test_construction_errors_match_r():
    assert _message(handler_beepr) == _BEEPR
    assert _message(handler_brrr) == _BRRR
    assert _message(handler_notifier) == _NOTIFIER
    assert _message(handler_ntfy) == _NTFY
    assert _message(handler_pbmcapply) == _PBMCAPPLY
    assert _message(handler_rpushbullet) == _RPUSHBULLET


def test_rstudio_and_shiny_fail_when_run():
    rstudio = handler_rstudio(enable=True)
    shiny = handler_shiny(enable=True)
    assert rstudio.classes[0] == "rstudio_progression_handler"
    assert shiny.classes[0] == "shiny_progression_handler"
    assert rstudio._env["target"] == "gui"
    assert shiny._env["target"] == "gui"
    assert _message(lambda: _two_steps(rstudio)) == _RSTUDIO
    assert _message(lambda: _two_steps(shiny)) == _SHINY


def test_with_progress_shiny_does_not_run_expr():
    ran = {"value": False}

    def expr():
        ran["value"] = True
        return 2

    assert _message(lambda: with_progress_shiny(expr)) == _SHINY
    assert ran["value"] is False


def test_progress_progressr_types_and_amounts():
    seen = []

    def push(config, state, progression, **kwargs):
        seen.append((progression["type"], progression["amount"]))

    handler = make_progression_handler(
        "record",
        reporter={"initiate": push, "update": push, "finish": push},
        enable=True,
        intrusiveness=1,
        interval=0,
    )

    def body():
        bar = progress_progressr()
        bar["init"](3)
        bar["step"]()
        bar["step"]()
        bar["term"]()
        return 3

    result = with_progress(
        body,
        handlers=handler,
        enable=True,
        interval=0,
        delay_terminal=False,
        delay_stdout=False,
        delay_conditions=(),
    )
    assert result == 3
    assert seen == _EVENTS
