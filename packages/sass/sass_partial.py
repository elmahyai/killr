from ._common import as_layer
from .sass_options import sass_options


def sass_partial(rules, bundle, options=None, output=None,
                 write_attachments=None, cache=None, cache_key_extra=None):
    if not hasattr(bundle, "layers"):
        raise TypeError("`bundle` must be a `sass_bundle()` object.")
    layer = as_layer(bundle)
    layer.rules = rules
    try:
        import sass_kernel
    except ImportError as exc:
        raise ImportError("sass_kernel is required for sass_partial compilation") from exc
    opts = options or sass_options()
    style = {0: "nested", 1: "expanded", 2: "compact", 3: "compressed"}[opts["output_style"]]
    css = sass_kernel.compile_scss(
        (layer.rules if isinstance(layer.rules, str) else "\n".join(layer.rules or [])),
        output_style=style,
        include_path=[x for x in opts["include_path"].split(":") if x],
        precision=opts["precision"], indented_syntax=opts["indented_syntax"],
        source_comments=opts["source_comments"], indent=opts["indent"],
        linefeed={"\n": "lf", "\r": "cr", "\r\n": "crlf", "\n\r": "lfcr"}[opts["linefeed"]],
    )
    if output is not None:
        with open(output, "w", encoding="utf-8", newline="") as stream:
            stream.write(css)
        return output
    return css
