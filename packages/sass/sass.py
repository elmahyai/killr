"""Translation of sass::sass().

The compile runs in the libsass wrapper (sass_kernel). Options use R's
sass_options() names and defaults: output_style "expanded", precision 5,
indent_width 2, linefeed "lf".

Caching is not reproduced. R's default cache writes compiled CSS to disk and
returns it on later calls; this translation always compiles. The CSS text is
the same either way.
"""

import os

from .as_sass import as_sass

_OUTPUT_STYLES = ("nested", "expanded", "compact", "compressed")
_LINEFEEDS = {"lf": "lf", "cr": "cr", "crlf": "crlf", "lfcr": "lfcr"}
_OPTION_NAMES = {
    "precision", "output_style", "indented_syntax", "include_path", "source_comments",
    "indent_type", "indent_width", "linefeed", "output_path", "source_map_file",
    "source_map_root", "source_map_embed", "source_map_contents", "omit_source_map_url",
}


def _sass_options(options):
    """Normalize a dict of sass_options() arguments into kernel arguments."""
    opts = dict(options or {})
    unknown = set(opts) - _OPTION_NAMES
    if unknown:
        raise ValueError(
            "The following arguments are not supported by `sass_options()`: "
            + ", ".join(sorted(unknown))
        )
    style = opts.get("output_style", "expanded")
    if style not in _OUTPUT_STYLES:
        raise ValueError("output style not supported.")
    indent_type = opts.get("indent_type", "space")
    if indent_type not in ("space", "tab"):
        raise ValueError('invalid indent type. Please specify "space" or "tab".')
    width = min(10, max(0, opts.get("indent_width", 2)))
    linefeed = opts.get("linefeed", "lf")
    if linefeed not in _LINEFEEDS:
        raise ValueError("invalid linefeed.")
    include_path = opts.get("include_path", "")
    if isinstance(include_path, (list, tuple)):
        include_path = ":".join(str(p) for p in include_path)
    return {
        "output_style": style,
        "precision": opts.get("precision", 5),
        "indented_syntax": opts.get("indented_syntax", False),
        "include_path": [p for p in include_path.split(":") if p] or None,
        "source_comments": opts.get("source_comments", False),
        "indent": ("\t" if indent_type == "tab" else " ") * width,
        "linefeed": _LINEFEEDS[linefeed],
    }


def sass(input=None, options=None, output=None, write_attachments=None,
         cache=None, cache_key_extra=None):
    import sass_kernel

    if write_attachments is True and output is None:
        raise ValueError("sass(write_attachments=TRUE) cannot be used when output=NULL")
    kwargs = _sass_options(options)
    source = as_sass(input)
    if not isinstance(source, str):
        raise TypeError("only a single character string can be compiled")
    css = sass_kernel.compile_scss(source, **kwargs)
    if callable(output):
        output = output(options or {}, None)
    if output is not None:
        out = str(output)
        outdir = os.path.dirname(out) or "."
        if not os.path.isdir(outdir):
            raise ValueError(f"The output directory '{outdir}' does not exist")
        with open(out, "wb") as fh:
            fh.write(css.encode("utf-8"))
        return out
    return css
