"""Small Python equivalents of sass's layer, bundle, and option records."""

from __future__ import annotations

from pathlib import Path
import re
import shutil


class SassLayer(dict):
    class_name = "sass_layer"


class SassBundle(dict):
    class_name = "sass_bundle"


class SassOptions(dict):
    class_name = "sass_options"


_GLOBAL_OPTIONS: dict = {}


def layer(**kwargs) -> SassLayer:
    values = {
        "functions": None,
        "defaults": None,
        "mixins": None,
        "rules": None,
        "declarations": None,
        "html_deps": None,
        "file_attachments": {},
    }
    values.update(kwargs)
    return SassLayer(values)


def bundle(*values) -> SassBundle:
    layers = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, SassBundle):
            layers.extend(value["layers"])
        elif isinstance(value, SassLayer):
            layers.append(value)
        elif isinstance(value, dict):
            layers.append(layer(defaults=value))
        else:
            layers.append(layer(rules=value))
    return SassBundle({"layers": layers})


def options(**kwargs) -> SassOptions:
    precision = kwargs.get("precision", 5)
    width = min(10, max(0, kwargs.get("indent_width", 2)))
    indent_type = kwargs.get("indent_type", "space")
    if indent_type not in ("space", "tab"):
        raise ValueError('invalid indent type. Please specify "space" or "tab".')
    style = kwargs.get("output_style", "expanded")
    if style not in ("nested", "expanded", "compact", "compressed"):
        raise ValueError("output style not supported.")
    linefeed_name = kwargs.get("linefeed", "lf")
    linefeeds = {"lf": "\n", "cr": "\r", "crlf": "\r\n", "lfcr": "\n\r"}
    if linefeed_name not in linefeeds:
        raise ValueError("invalid linefeed.")
    include = kwargs.get("include_path", "")
    if isinstance(include, (str, Path)):
        include = str(include)
    else:
        include = ":".join(str(x) for x in include)
    return SassOptions({
        "precision": precision,
        "output_style": {"nested": 0, "expanded": 1, "compact": 2, "compressed": 3}[style],
        "indented_syntax": kwargs.get("indented_syntax", False),
        "include_path": include,
        "source_comments": kwargs.get("source_comments", False),
        "indent": ("\t" if indent_type == "tab" else " ") * width,
        "linefeed": linefeeds[linefeed_name],
        "output_path": kwargs.get("output_path", ""),
        "source_map_file": kwargs.get("source_map_file", ""),
        "source_map_root": kwargs.get("source_map_root", ""),
        "source_map_embed": kwargs.get("source_map_embed", False),
        "source_map_contents": kwargs.get("source_map_contents", False),
        "omit_source_map_url": kwargs.get("omit_source_map_url", False),
    })


def as_layer(value) -> SassLayer:
    if isinstance(value, SassLayer):
        return value
    if isinstance(value, SassBundle):
        layers = value["layers"]
        return layer(
            functions=[x["functions"] for x in layers if x["functions"] is not None] or None,
            defaults=next((x["defaults"] for x in reversed(layers) if x["defaults"] is not None), None),
            mixins=[x["mixins"] for x in layers if x["mixins"] is not None] or None,
            rules=[x["rules"] for x in layers if x["rules"] is not None] or None,
            declarations=[x["declarations"] for x in layers if x["declarations"] is not None] or None,
            html_deps=[x["html_deps"] for x in layers if x["html_deps"] is not None] or None,
            file_attachments={k: v for x in layers for k, v in x["file_attachments"].items()},
        )
    return layer(rules=value)


def read_layer_file(path) -> SassLayer:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    marker = re.compile(r"^/\*--[ \t]*scss:(functions|defaults|rules|mixins)[ \t]*--\*/$")
    found = [(i, m.group(1)) for i, line in enumerate(lines) if (m := marker.match(line))]
    if not found:
        return layer(rules=lines)
    values = {kind: [] for _, kind in found}
    for n, (start, kind) in enumerate(found):
        end = found[n + 1][0] if n + 1 < len(found) else len(lines)
        values[kind].extend(lines[start + 1:end])
    return layer(**values)


def copy_attachments(attachments, output_path):
    destination = Path(output_path)
    if not destination.is_dir():
        raise FileNotFoundError(f"Directory '{output_path}' not found or is not a directory")
    for dest, source in dict(attachments).items():
        source = Path(source)
        dest = destination / dest
        if source.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
            for item in source.iterdir():
                target = dest / item.name
                shutil.copytree(item, target, dirs_exist_ok=True) if item.is_dir() else shutil.copy2(item, target)
        else:
            if str(dest).endswith("/") or str(dest).endswith("\\"):
                dest = dest / source.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
"""Small Python representations of sass 0.4.10's R-side helper objects."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import tempfile


@dataclass
class FontCollection:
    families: list[str]
    html_deps: list[Any] = field(default_factory=list)
    default_flag: bool = True
    quote: bool = True

    def __getitem__(self, key):
        return getattr(self, key)


@dataclass
class SassLayer:
    functions: Any = None
    defaults: Any = None
    mixins: Any = None
    rules: Any = None
    declarations: Any = None
    html_deps: Any = None
    file_attachments: list[str] = field(default_factory=list)
    tags: Any = None

    def __getitem__(self, key):
        return getattr(self, key)


@dataclass
class SassBundle:
    layers: list[SassLayer] = field(default_factory=list)

    def __getitem__(self, key):
        return getattr(self, key)


@dataclass
class FontObject:
    family: str
    href: str | None = None
    css: str | None = None
    src: str | None = None
    weight: Any = None
    style: Any = None
    display: Any = None
    stretch: Any = None
    variant: Any = None
    unicode_range: Any = None


def quote_families(family) -> str:
    values = family if isinstance(family, (list, tuple)) else [family]
    return ", ".join(
        f"'{x}'" if isinstance(x, str) and " " in x and not (x.startswith("'") or x.startswith('"')) else str(x)
        for x in values
    )


def css_font_face(values: dict[str, Any]) -> str:
    lines = ["@font-face {"]
    for key in ("family", "src", "weight", "style", "display", "stretch", "variant", "unicode_range"):
        value = values.get(key)
        if value is not None:
            prop = "unicode-range" if key == "unicode_range" else key
            lines.append(f"  {prop}: {value};")
    lines.append("}")
    return "\n".join(lines)


def output_path(basename="sass", dirname=None, fileext=None, path=None, options=None, suffix=None):
    dirname = basename if dirname is None else dirname
    path = tempfile.gettempdir() if path is None else path
    options = options or {}
    if fileext is None:
        fileext = ".min.css" if options.get("output_style") in (2, 3, "compact", "compressed") else ".css"
    out_dir = Path(path) / (f"{dirname}{suffix}" if suffix is not None else tempfile.mktemp(prefix=dirname, dir=path).split("/")[-1])
    out_dir.mkdir(parents=True, exist_ok=True)
    return str(out_dir / f"{basename}{fileext}")
"""Small Python representations used by the translated sass helpers."""

from dataclasses import dataclass, field
from pathlib import Path
import tempfile


@dataclass
class SassLayer:
    functions: object = None
    defaults: object = None
    mixins: object = None
    rules: object = None
    html_deps: object = None
    file_attachments: object = field(default_factory=list)
    declarations: object = None


@dataclass
class SassBundle:
    layers: dict = field(default_factory=dict)


_caches = {}
_cache_dir = None


class FileCache:
    def __init__(self, directory, max_size=40 * 1024**2, max_age=float("inf")):
        self.directory = str(Path(directory).expanduser().resolve())
        self.max_size = max_size
        self.max_age = max_age

    def dir(self):
        return self.directory


def cache_context_dir():
    global _cache_dir
    if _cache_dir is None:
        _cache_dir = str((Path(tempfile.gettempdir()) / "sass").resolve())
    path = Path(_cache_dir)
    try:
        path.mkdir(parents=True, exist_ok=True)
        return str(path)
    except OSError:
        fallback = Path(tempfile.mkdtemp(prefix="sass-"))
        return str(fallback.resolve())


# Compatibility helpers for the translated layer wrappers above.  The package
# already uses dataclasses for these records, so expose the same records here.
def layer(**kwargs):
    values = dict(functions=None, defaults=None, mixins=None, rules=None,
                  declarations=None, html_deps=None, file_attachments={})
    values.update(kwargs)
    return SassLayer(**values)


def bundle(*values):
    layers = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, SassBundle):
            layers.extend(value.layers.values() if isinstance(value.layers, dict) else value.layers)
        elif isinstance(value, SassLayer):
            layers.append(value)
        elif isinstance(value, dict):
            layers.append(layer(defaults=value))
        else:
            layers.append(layer(rules=value))
    return SassBundle({str(i): item for i, item in enumerate(layers)})


def as_layer(value):
    if isinstance(value, SassLayer):
        return value
    if isinstance(value, SassBundle):
        layers = list(value.layers.values()) if isinstance(value.layers, dict) else value.layers
        return layer(
            functions=[x.functions for x in layers if x.functions is not None] or None,
            defaults=next((x.defaults for x in reversed(layers) if x.defaults is not None), None),
            mixins=[x.mixins for x in layers if x.mixins is not None] or None,
            rules=[x.rules for x in layers if x.rules is not None] or None,
            declarations=[x.declarations for x in layers if x.declarations is not None] or None,
            html_deps=[x.html_deps for x in layers if x.html_deps is not None] or None,
            file_attachments={k: v for x in layers for k, v in (x.file_attachments or {}).items()},
        )
    return layer(rules=value)


def read_layer_file(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    marker = re.compile(r"^/\*--[ \t]*scss:(functions|defaults|rules|mixins)[ \t]*--\*/$")
    found = [(i, m.group(1)) for i, line in enumerate(lines) if (m := marker.match(line))]
    if not found:
        return layer(rules=lines)
    values = {kind: [] for _, kind in found}
    for n, (start, kind) in enumerate(found):
        end = found[n + 1][0] if n + 1 < len(found) else len(lines)
        values[kind].extend(lines[start + 1:end])
    return layer(**values)
