"""Python translation of the R package progressr.

Progress conditions are signaled to handlers. ``with_progress`` and
``without_progress`` take a zero-argument callable, because Python evaluates
arguments before the call.
"""

from progressr.aggregator import progress_aggregator
from progressr.backends import handler_progress, handler_tkprogressbar
from progressr.bars import handler_txtprogressbar, handler_winprogressbar
from progressr.cli_handlers import handler_cli, handler_pbcol, handler_tutorial
from progressr.condition import progression
from progressr.demo import slow_sqrt, slow_sqrt_p, slow_sum, slow_sum_p
from progressr.evaluate import with_progress, without_progress
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
from progressr.handlers import handlers
from progressr.progressor import progressor
from progressr.reporters import (
    handler_ascii_alert,
    handler_debug,
    handler_filesize,
    handler_newline,
    handler_slowdown,
    handler_void,
)

__all__ = [
    "handler_ascii_alert",
    "handler_beepr",
    "handler_brrr",
    "handler_cli",
    "handler_debug",
    "handler_filesize",
    "handler_newline",
    "handler_notifier",
    "handler_ntfy",
    "handler_pbcol",
    "handler_pbmcapply",
    "handler_progress",
    "handler_rpushbullet",
    "handler_rstudio",
    "handler_shiny",
    "handler_slowdown",
    "handler_tkprogressbar",
    "handler_tutorial",
    "handler_txtprogressbar",
    "handler_void",
    "handler_winprogressbar",
    "handlers",
    "make_progression_handler",
    "progress_aggregator",
    "progress_progressr",
    "progression",
    "progressor",
    "slow_sqrt",
    "slow_sqrt_p",
    "slow_sum",
    "slow_sum_p",
    "with_progress",
    "with_progress_shiny",
    "without_progress",
]
