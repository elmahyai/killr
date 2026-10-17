"""Read vignette metadata lines and the vignette engine registry."""

import os
import re
from pathlib import Path


def _metadata(lines, tag):
    compiled = re.compile(
        r"[ \t\r\f\v]*%+[ \t\r\f\v]*\\Vignette"
        + tag
        + r"\{([^}]*(\{[^}]*\})*[^}]*)\}.*"
    )
    found = []
    for line in lines:
        if compiled.search(line):
            found.append(compiled.sub(r"\1", line).strip())
    return found


def get_vignette_engine(lines):
    engines = _metadata(lines, "Engine")
    return engines[0] if engines else "utils::Sweave"


def vignette_info(file):
    """Title, dependencies, keywords, and engine from one vignette file."""
    lines = Path(file).read_text(encoding="utf-8", errors="replace").splitlines()
    titles = _metadata(lines, "IndexEntry")
    title = titles[0] if titles else ""
    depends = _metadata(lines, "Depends")
    if depends:
        depends = [part for part in re.split(r", *", depends[0])]
    keywords = _metadata(lines, "Keywords")
    if not keywords:
        keywords = _metadata(lines, "Keyword")
    else:
        keywords = [part for part in re.split(r", *", keywords[0])]
    return {
        "file": Path(file).name,
        "title": title,
        "depends": depends,
        "keywords": keywords,
        "engine": get_vignette_engine(lines),
    }


def _quote(text):
    return f"\u2018{text}\u2019"


def _lib_paths():
    roots = []
    env = os.environ.get("R_LIBS")
    if env:
        roots.extend(env.split(os.pathsep))
    roots.append(str(Path.home() / "R" / "library"))
    roots.extend([
        "/usr/local/lib/R/site-library",
        "/usr/lib/R/site-library",
        os.path.join(os.environ.get("R_HOME", "/usr/lib/R"), "library"),
    ])
    seen = []
    for root in roots:
        if root and root not in seen and Path(root).is_dir():
            seen.append(root)
    return seen


def _package_exists(name):
    for root in _lib_paths():
        if (Path(root) / name / "DESCRIPTION").is_file():
            return True
    return False


_SWEAVE = {
    "name": "Sweave",
    "package": "utils",
    "pattern": "[.][rRsS](nw|tex)$",
    "weave": None,
    "tangle": None,
    "aspell": {"filter": "Sweave"},
}
_REGISTRY = {"utils::Sweave": dict(_SWEAVE)}


def _engine_key(name, package=None, package_given=False):
    key = name.split("::")
    if len(key) == 1:
        if not package_given:
            raise ValueError("Vignette engine package not specified")
        if package is None:
            raise ValueError("replacement has length zero")
        return [package, key[0]]
    if len(key) != 2:
        raise ValueError(f"Unsupported engine name {_quote(name)}")
    return key


class _Missing:
    pass


_MISSING = _Missing()


def vignette_engine(name, weave=_MISSING, tangle=_MISSING, pattern=None, package=_MISSING, aspell=None):
    """Look up a vignette engine, or register one when weave is supplied."""
    if isinstance(weave, _Missing):
        if name == "Sweave":
            key = _engine_key(name, "utils", package_given=True)
        else:
            key = _engine_key(name, None if isinstance(package, _Missing) else package, package_given=not isinstance(package, _Missing))
        if not _package_exists(key[0]):
            raise ValueError(f"there is no package called {_quote(key[0])}")
        registered = _REGISTRY.get("::".join(key))
        if registered is None:
            raise ValueError(f"Vignette engine {_quote('::'.join(key))} is not registered")
        return registered
    if name in ("Sweave", "utils::Sweave"):
        raise ValueError(f"Cannot change the {_quote('Sweave')} engine or use an engine of that name")
    given = None if isinstance(package, _Missing) else package
    key = _engine_key(name, given, package_given=True)
    if given is not None and key[0] != given:
        raise ValueError(f"Engine name {_quote(name)} and package {_quote(given)} do not match")
    if weave is None:
        _REGISTRY.pop("::".join(key), None)
        return None
    if not callable(weave):
        raise ValueError(f"Argument {_quote('weave')} must be a function and not {_quote(type(weave).__name__)}")
    if isinstance(tangle, _Missing) or not callable(tangle):
        shown = "NULL" if isinstance(tangle, _Missing) or tangle is None else type(tangle).__name__
        raise ValueError(f"Argument {_quote('tangle')} must be a function and not {_quote(shown)}")
    if pattern is None:
        pattern = "[.][rRsS](nw|tex)$"
    if not isinstance(pattern, str):
        raise ValueError(f"Argument {_quote('pattern')} must be a character vector or NULL and not {_quote(type(pattern).__name__)}")
    result = {
        "name": key[1],
        "package": key[0],
        "pattern": pattern,
        "weave": weave,
        "tangle": tangle,
        "aspell": {} if aspell is None else aspell,
    }
    _REGISTRY["::".join(key)] = result
    return result
