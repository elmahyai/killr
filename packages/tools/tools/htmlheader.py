"""HTML page header from tools 4.5.0."""

from __future__ import annotations

import locale


def _file_path(*parts: str) -> str:
    if parts and parts[0] == "":
        return "/" + "/".join(part.strip("/") for part in parts[1:] if part != "")
    return "/".join(parts)


def mime_canonical_encoding(encoding: str) -> str:
    """The charset name R writes into an HTML content-type."""
    if encoding in ("", "unknown"):
        encoding = locale.getpreferredencoding(False)
    encoding = encoding.lower()
    encoding = encoding.replace("iso_8859-", "iso-8859-").replace("iso8859-", "iso-8859-")
    aliases = {
        "latin1": "iso-8859-1",
        "latin2": "iso-8859-2",
        "latin3": "iso-8859-3",
        "latin4": "iso-8859-4",
        "cyrillic": "iso-8859-5",
        "arabic": "iso-8859-6",
        "greek": "iso-8859-7",
        "hebrew": "iso-8859-8",
        "latin5": "iso-8859-9",
        "latin6": "iso-8859-10",
        "latin8": "iso-8859-14",
        "latin-9": "iso-8859-15",
        "latin10": "iso-8859-16",
        "utf8": "utf-8",
        "ascii": "us-ascii",
    }
    return aliases.get(encoding, encoding)


def html_header(
    title: str = "R",
    logo: bool = True,
    up: str | None = None,
    top: str | None = "",
    rhome: str = "",
    css: str | None = None,
    header_title: str | None = None,
    output_encoding: str = "UTF-8",
) -> list[str]:
    """The lines of an R HTML help header."""
    if css is None:
        css = _file_path(rhome, "doc/html/R.css")
    if header_title is None:
        header_title = f"R: {title}"
    if top == "" and top is not None:
        top = _file_path(rhome, "doc/html/index.html")
    result = [
        "<!DOCTYPE html>",
        "<html>",
        f"<head><title>{header_title}</title>",
        f'<meta http-equiv="Content-Type" content="text/html; charset={mime_canonical_encoding(output_encoding)}" />',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes" />',
        f'<link rel="stylesheet" type="text/css" href="{css}" />',
        '</head><body><div class="container">',
        f"<h1> {title}",
    ]
    if logo:
        result.append(
            f'<img class="toplogo" src="{_file_path(rhome, "doc/html/Rlogo.svg")}" alt="[R logo]" />'
        )
    result.extend(["</h1>", "<hr/>"])
    if up is not None or top is not None:
        result.append('<div style="text-align: center;">')
        if up is not None:
            result.append(
                f'<a href="{up}"><img class="arrow" src="{_file_path(rhome, "doc/html/left.jpg")}" alt="[Up]" /></a>'
            )
        if top is not None:
            result.append(
                f'<a href="{top}"><img class="arrow" src="{_file_path(rhome, "doc/html/up.jpg")}" alt="[Top]" /></a>'
            )
        result.append("</div>")
    return result
