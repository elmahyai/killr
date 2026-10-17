"""Python translation of the R package evaluate."""

from evaluate.core import (
    create_traceback,
    evaluate,
    line_prompt,
    replay,
    try_capture_stack,
)
from evaluate.extras import (
    flush_console,
    inject_funs,
    local_reproducible_output,
    remove_hooks,
    set_hooks,
)
from evaluate.graphics import draw_plot, lines, par, plot, plot_new, points, text, trim_intermediate_plots
from evaluate.handlers import new_output_handler
from evaluate.parse import parse_all
from evaluate.show import cat, r_print
from evaluate.types import (
    Evaluation,
    RecordedPlot,
    Source,
    is_error,
    is_message,
    is_recordedplot,
    is_source,
    is_warning,
)

__all__ = [
    "Evaluation",
    "RecordedPlot",
    "Source",
    "cat",
    "create_traceback",
    "draw_plot",
    "evaluate",
    "flush_console",
    "inject_funs",
    "is_error",
    "is_message",
    "is_recordedplot",
    "is_source",
    "is_warning",
    "line_prompt",
    "lines",
    "local_reproducible_output",
    "new_output_handler",
    "par",
    "parse_all",
    "plot",
    "plot_new",
    "points",
    "r_print",
    "remove_hooks",
    "replay",
    "set_hooks",
    "text",
    "trim_intermediate_plots",
    "try_capture_stack",
]
