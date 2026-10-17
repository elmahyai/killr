"""Python translation of the R package sys.

The import name is ``r_sys`` because ``sys`` is the Python standard library.
Processes are started with ``subprocess``. ``exec_status`` returns the wait
status word: a normal exit is the code shifted left by 8, and a signal is
the signal number.
"""

from r_sys.deprecated import eval_fork, eval_safe
from r_sys.exec import exec_background, exec_internal, exec_status, exec_wait
from r_sys.quote import windows_quote
from r_sys.rbin import r_background, r_internal, r_wait
from r_sys.text import as_text

__all__ = [
    "as_text",
    "eval_fork",
    "eval_safe",
    "exec_background",
    "exec_internal",
    "exec_status",
    "exec_wait",
    "r_background",
    "r_internal",
    "r_wait",
    "windows_quote",
]
