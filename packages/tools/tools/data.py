"""Data objects shipped with tools."""

import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def adobe_glyphs():
    """The Adobe glyph list: names and Unicode code points."""
    return json.loads((_HERE / "adobe_glyphs.json").read_text(encoding="utf-8"))


def charset_to_unicode():
    """256 by 14 Unicode code points for the character sets tools knows."""
    rows = json.loads((_HERE / "charset.json").read_text(encoding="utf-8"))
    return {
        "columns": [
            "ISOLatin1",
            "ISOLatin2",
            "ISOLatin7",
            "ISOLatin9",
            "Cyrillic",
            "Greek",
            "KOI8R",
            "KOI8U",
            "CP1250",
            "CP1251",
            "CP1252",
            "CP1253",
            "CP1257",
            "AdobeSymbol",
        ],
        "values": rows,
    }
