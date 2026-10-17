"""Translation of sass::as_sass().

R dispatches on the class of the input (as_sass_.NULL, _.character, _.list,
_.sass_layer, _.sass_bundle, _.font_collection, and so on). Python uses the
same dispatch order with isinstance checks.

Python representation of R values:
- None is NULL.
- A dict is a named list. An empty-string key is an unnamed element.
- A list is an unnamed list.
- A tuple is a character vector, joined with newlines.
- A str is a length-one character vector.

The result carries R's html_dependencies attribute as `.html_dependencies`:
a list of HtmlDep objects, or None when R would have no attribute. The
dependencies are found by the same walk as R's find_dependencies(). A font
dependency is returned unrendered, as R's tagFunction is. Rendering happens
when the dependency is used, through font_google.render_google_local.
"""

from ._common import FontCollection, SassBundle, SassLayer
from ._sass_values import r_chr


class SassHtml(str):
    """A length-one as_sass() result with its html dependencies."""

    html_dependencies = None


class SassHtmlVector(list):
    """A vector as_sass() result (a font collection with quote = FALSE)."""

    html_dependencies = None


def as_sass(input):
    """Return the Sass source text for input, with its html dependencies attached."""
    text = _as_sass(input)
    deps = find_dependencies(input) or None
    return _attach(text, deps)


def _attach(text, deps):
    if isinstance(text, list):
        out = SassHtmlVector(text)
    else:
        out = SassHtml(text)
    out.html_dependencies = deps
    return out


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def find_dependencies(x):
    """R find_dependencies(): dependencies from children first, then the object's own."""
    own = None
    children = []
    if isinstance(x, (SassBundle, SassLayer)):
        from .as_sass_layer import as_sass_layer

        layer = as_sass_layer(x)
        own = layer.html_deps
        # R sets html_deps to NULL before it recurses, so the layer's own
        # html_deps are not visited a second time.
        children = [layer.functions, layer.defaults, layer.mixins, layer.rules,
                    layer.declarations, layer.file_attachments]
    elif isinstance(x, FontCollection):
        # Its families are strings and its html_deps are font functions, which carry
        # no dependencies of their own, so the walk adds nothing beyond its own list.
        own = x.html_deps
    elif isinstance(x, (SassHtml, SassHtmlVector)):
        own = x.html_dependencies
    elif isinstance(x, dict):
        children = list(x.values())
    elif isinstance(x, list):
        children = list(x)

    deps = []
    for child in children:
        deps.extend(find_dependencies(child))
    deps.extend(_as_list(own))
    return deps


def _as_sass(x):
    if x is None:
        return "null"
    if isinstance(x, SassLayer):
        return _layer_text(x)
    if isinstance(x, SassBundle):
        from .as_sass_layer import as_sass_layer, layers_of

        if not layers_of(x):
            return ""
        return _as_sass(as_sass_layer(x))
    if isinstance(x, FontCollection):
        out = [f"{f} !default" if x.default_flag is True else f for f in x.families]
        return out[0] if len(out) == 1 else out
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, (int, float)):
        return r_chr(x)
    if isinstance(x, str):
        return x
    if isinstance(x, tuple):
        return "\n".join(v if isinstance(v, str) else r_chr(v) for v in x)
    if isinstance(x, dict):
        parts = [f"${k}: {_as_sass(v)};" if k else _as_sass(v) for k, v in x.items()]
        return "\n".join(parts)
    if isinstance(x, list):
        return "\n".join(_as_sass(v) for v in x)
    raise TypeError(f"as_sass() not implemented for object of class: '{type(x).__name__}'")


def _layer_text(layer):
    parts = []
    for value in (layer.functions, layer.defaults, layer.mixins, layer.declarations, layer.rules):
        if value is not None:
            parts.append(_as_sass(value))
    return "\n".join(parts)
