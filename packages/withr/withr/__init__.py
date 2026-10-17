"""Python translation of the R package withr 3.0.3.

Each R source file is one module, and each export is a function with the R
name. ``code`` arguments are zero-argument callables, because R evaluates them
lazily and Python would otherwise run them first. ``local_*`` functions attach
their reset to a frame: use ``with scope():`` as the frame, or pass
``_local_envir``. Named gaps raise ``NamedGap``; see the proofs and the
module docstrings for each gap.
"""

from ._gap import NamedGap
from ._scope import GLOBAL, scope
from .collate import local_collate, with_collate
from .connection import (
    local_connection,
    local_db_connection,
    with_connection,
    with_db_connection,
)
from .deferred import defer, defer_parent, deferred_clear, deferred_run, global_defer
from .devices import (
    local_bmp,
    local_cairo_pdf,
    local_cairo_ps,
    local_jpeg,
    local_pdf,
    local_png,
    local_postscript,
    local_svg,
    local_tiff,
    local_xfig,
    with_bmp,
    with_cairo_pdf,
    with_cairo_ps,
    with_jpeg,
    with_pdf,
    with_png,
    with_postscript,
    with_svg,
    with_tiff,
    with_xfig,
)
from .directory import local_dir, with_dir
from .envvar import local_envvar, with_envvar
from .factory import local_, with_
from .files import local_file, with_file
from .language import local_language, with_language
from .libpaths import (
    libpaths,
    local_libpaths,
    local_temp_libpaths,
    with_libpaths,
    with_temp_libpaths,
)
from .locale_settings import local_locale, with_locale
from .makevars import local_makevars, makevars_user, set_makevars, with_makevars
from .namespace import (
    lookup,
    local_environment,
    local_namespace,
    local_package,
    with_environment,
    with_namespace,
    with_package,
    search,
)
from .options import local_options, with_options
from .par import local_par, with_par
from .path import local_path, with_path
from .rng import local_rng_version, with_rng_version
from .seed import local_preserve_seed, local_seed, with_preserve_seed, with_seed
from .sink import local_message_sink, local_output_sink, with_message_sink, with_output_sink
from .tempfiles import local_tempdir, local_tempfile, with_tempdir, with_tempfile
from .timezone import local_timezone, with_timezone

__all__ = [
    "GLOBAL",
    "NamedGap",
    "scope",
    "defer",
    "defer_parent",
    "deferred_clear",
    "deferred_run",
    "global_defer",
    "local_",
    "with_",
    "local_bmp",
    "local_cairo_pdf",
    "local_cairo_ps",
    "local_collate",
    "local_connection",
    "local_db_connection",
    "local_dir",
    "local_environment",
    "local_envvar",
    "local_file",
    "local_jpeg",
    "local_language",
    "local_libpaths",
    "libpaths",
    "local_locale",
    "local_makevars",
    "local_message_sink",
    "local_namespace",
    "lookup",
    "local_options",
    "local_output_sink",
    "local_package",
    "local_par",
    "local_path",
    "local_pdf",
    "local_png",
    "local_postscript",
    "local_preserve_seed",
    "local_rng_version",
    "local_seed",
    "local_svg",
    "local_temp_libpaths",
    "local_tempdir",
    "local_tempfile",
    "local_tiff",
    "local_timezone",
    "local_xfig",
    "makevars_user",
    "set_makevars",
    "with_bmp",
    "with_cairo_pdf",
    "with_cairo_ps",
    "with_collate",
    "with_connection",
    "with_db_connection",
    "with_dir",
    "with_environment",
    "with_envvar",
    "with_file",
    "with_jpeg",
    "with_language",
    "with_libpaths",
    "with_locale",
    "with_makevars",
    "with_message_sink",
    "with_namespace",
    "with_options",
    "with_output_sink",
    "with_package",
    "search",
    "with_par",
    "with_path",
    "with_pdf",
    "with_png",
    "with_postscript",
    "with_preserve_seed",
    "with_rng_version",
    "with_seed",
    "with_svg",
    "with_temp_libpaths",
    "with_tempdir",
    "with_tempfile",
    "with_tiff",
    "with_timezone",
    "with_xfig",
]
