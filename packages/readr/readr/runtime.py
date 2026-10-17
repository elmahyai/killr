"""Edition, threads, and the bundled example files."""

from __future__ import annotations

import os
from pathlib import Path

from withr._options import get_option, options
from withr._options import local_options, with_options

_EXAMPLES = Path(__file__).with_name("extdata")
_MISSING = object()


def edition_get() -> int:
    """The active readr edition. The default is 2."""
    return int(get_option("readr.edition", 2))


def edition_first() -> bool:
    return edition_get() == 1


def _check_edition(edition) -> int:
    value = int(edition)
    if value not in (1, 2):
        raise ValueError("edition must be 1 or 2")
    return value


def with_edition(edition, code):
    """Run `code()` with a different readr edition."""
    value = _check_edition(edition)
    return with_options({"readr.edition": value}, code)


def local_edition(edition):
    """Change the edition until the surrounding block ends."""
    value = _check_edition(edition)
    return local_options(**{"readr.edition": value})


def show_progress() -> bool:
    """True only when progress was requested and this session is interactive."""
    if get_option("readr.show_progress") is not True:
        return False
    if get_option("rstudio.notebook.executing") is True:
        return False
    try:
        return os.isatty(0)
    except OSError:
        return False


def should_show_types():
    """NULL when the caller should decide. TRUE or FALSE when the option is set."""
    option = get_option("readr.show_col_types", None)
    if option is True:
        return True
    if option is False:
        return False
    return None


def should_read_lazy() -> bool:
    """Whether the `readr.read_lazy` option asks for a lazy read."""
    return get_option("readr.read_lazy", False) is True


def readr_threads() -> int:
    """Thread count from the option, then VROOM_THREADS, then the CPU count."""
    value = get_option("readr.num_threads", None)
    if value is None:
        env = os.environ.get("VROOM_THREADS")
        value = int(env) if env else (os.cpu_count() or 1)
        options(**{"readr.num_threads": int(value)})
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = 1
    if value <= 0:
        value = 1
    return value


def readr_example(file=None):
    """Path to a bundled example, or the list of example names."""
    if file is None:
        return sorted(path.name for path in _EXAMPLES.iterdir() if path.is_file())
    path = _EXAMPLES / file
    if not path.is_file():
        raise FileNotFoundError(file)
    return str(path)
