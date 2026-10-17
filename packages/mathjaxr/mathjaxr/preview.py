"""Preview Rd files as HTML, text, or PDF-oriented output.

The HTML preview intentionally references MathJax's CDN.  The R package does
the same for previews and does not make the bundled MathJax asset available to
this translation.
"""

from __future__ import annotations

import html
import os
import re
import subprocess
import tempfile
import webbrowser
from pathlib import Path
from typing import Any

_TYPES = {"html", "txt", "text", "pdf"}
_MATHJAX_CDN = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"


def _locate_rd(name: str, working_dir: Path) -> Path:
    """Resolve an Rd basename as preview_rd does (man before the root)."""
    raw = Path(name).name
    has_extension = raw[-3:] in (".Rd", ".rd")
    suffixes = ("",) if has_extension else (".Rd", ".rd")
    for directory in (working_dir / "man", working_dir):
        for suffix in suffixes:
            candidate = directory / (raw + suffix)
            if candidate.is_file():
                return candidate
    raise FileNotFoundError(
        "Cannot find the specified Rd file in the current directory "
        "or in the 'man' subdirectory."
    )


def _rd_text(source: str) -> str:
    """Small dependency-free Rd-to-text renderer for preview use."""
    def section(tag: str) -> str:
        match = re.search(rf"\\{tag}\{{([^{{}}]*)\}}", source, re.DOTALL)
        return match.group(1).strip() if match else ""

    title = section("title")
    description = section("description")
    if title and description:
        # R's Rd2txt uses overstrikes for headings in terminal output.
        heading = "".join(f"_\b{char}" for char in title)
        label = "".join(f"_\b{char}" for char in "Description") + ":"
        return f"{heading}\n\n{label}\n\n     {description}\n\n"
    text = re.sub(r"\\(code|link|pkg|file|sQuote|emph|strong)\{([^{}]*)\}", r"\2", source)
    text = re.sub(r"\\[a-zA-Z]+", "", text).replace("{", "").replace("}", "")
    return text.strip() + "\n"


def _rd_html(source: str, stylesheet: str | None, dark: bool) -> str:
    """Render common Rd markup while preserving MathJax expressions."""
    title = re.search(r"\\title\{([^{}]*)\}", source)
    body = source
    body = re.sub(r"\\title\{([^{}]*)\}", "", body)
    body = re.sub(r"\\(description|details|note|author|usage|value)\{", "", body)
    body = re.sub(r"\\item\{([^{}]*)\}\s*", r"<dt>\1</dt><dd>", body)
    body = re.sub(r"\\(code|link|pkg|file|sQuote|emph|strong)\{([^{}]*)\}", r"<code>\2</code>", body)
    body = body.replace("\\eqn{", "$").replace("\\eqn{", "$")
    body = body.replace("}", "$")
    body = html.escape(body, quote=False)
    body = body.replace("&lt;code&gt;", "<code>").replace("&lt;/code&gt;", "</code>")
    body = body.replace("\n", "<br>\n")
    css = f'<link rel="stylesheet" href="{html.escape(stylesheet, quote=True)}">' if stylesheet else ""
    theme = "body { background: #202124; color: #e8eaed; }" if dark else ""
    heading = html.escape(title.group(1) if title else "")
    return (
        "<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\">"
        f"<title>{heading}</title>{css}<style>{theme}</style>"
        f'<script async src="{_MATHJAX_CDN}"></script>'
        "</head><body>\n" + body + "\n</body></html>\n"
    )


def preview_rd(
    Rdfile: str | os.PathLike[str],
    view: bool = True,
    type: str = "html",
    verbose: bool = False,
    dark: bool = False,
    **kwargs: Any,
) -> str:
    """Write a temporary preview for an Rd file and return its path.

    ``html`` is rendered locally and loads MathJax from its CDN at view time.
    ``txt``/``text`` writes a plain-text rendering.  ``pdf`` delegates to the
    installed ``R CMD Rd2pdf`` command when available.
    """
    if Rdfile is None:
        raise ValueError("Must specify the 'Rdfile' argument.")
    if type not in _TYPES:
        raise ValueError("arg 'type' must be one of 'html', 'txt', 'text', 'pdf'")
    kind = "txt" if type == "text" else type
    original = Path(Rdfile)
    workdir = original.parent if str(original.parent) != "" else Path.cwd()
    rd_path = _locate_rd(original.name, workdir).resolve()
    outfile = Path(tempfile.gettempdir()) / f"{rd_path.name}.{kind}"
    source = rd_path.read_text(encoding="utf-8")
    if verbose:
        print(f"Found Rd file: {rd_path.relative_to(workdir.resolve())}")
        print(f"Creating preview file: {outfile}")
    if kind == "html":
        css = kwargs.get("css")
        _ = os.environ.get("MATHJAXR_USECDN")
        outfile.write_text(_rd_html(source, str(css) if css else None, dark), encoding="utf-8")
        if view:
            webbrowser.open(outfile.as_uri())
    elif kind == "txt":
        outfile.write_text(_rd_text(source), encoding="utf-8")
        if view:
            print(outfile.read_text(encoding="utf-8"), end="")
    else:
        subprocess.run(
            ["R", "CMD", "Rd2pdf", "--no-index", "--no-description", "--force",
             "--batch", "--no-preview", f"--output={outfile}", str(rd_path)],
            check=True,
        )
        if view:
            webbrowser.open(outfile.as_uri())
    return str(outfile)


__all__ = ["preview_rd"]
