"""localeToCharset, osVersion, and packageVersion from utils 4.5.0."""

from __future__ import annotations

import os
from pathlib import Path


class UtilsError(Exception):
    """An error raised with R's stop message."""


_LATIN1 = {
    "aa", "af", "an", "br", "ca", "da", "de", "en", "es", "et", "eu", "fi",
    "fo", "fr", "ga", "gl", "gv", "id", "is", "it", "kl", "kw", "ml", "ms",
    "nb", "nn", "no", "oc", "om", "pt", "so", "sq", "st", "sv", "tl", "uz",
    "wa", "xh", "zu",
}
_LATIN2 = {"bs", "cs", "hr", "hu", "pl", "ro", "sk", "sl"}
_KNOWN = {
    "iso88591": "ISO8859-1",
    "iso88592": "ISO8859-2",
    "iso88593": "ISO8859-3",
    "iso88596": "ISO8859-6",
    "iso88597": "ISO8859-7",
    "iso88598": "ISO8859-8",
    "iso88599": "ISO8859-9",
    "iso885910": "ISO8859-10",
    "iso885913": "ISO8859-13",
    "iso885914": "ISO8859-14",
    "iso885915": "ISO8859-15",
    "cp1251": "CP1251",
    "cp1255": "CP1255",
    "eucjp": "EUC-JP",
    "euckr": "EUC-KR",
    "euctw": "EUC-TW",
    "georgianps": "GEORGIAN-PS",
    "koi8r": "KOI8-R",
    "koi8u": "KOI8-U",
    "tcvn": "TCVN",
    "big5": "BIG5",
    "gb2312": "GB2312",
    "gb18030": "GB18030",
    "gbk": "GBK",
    "tis-620": "TIS-620",
    "sjis": "SHIFT_JIS",
    "eucn": "GB2312",
    "big5-hkscs": "BIG5-HKSCS",
}
_LIBRARIES = (
    Path.home() / "R" / "x86_64-pc-linux-gnu-library" / "4.5",
    Path("/usr/local/lib/R/site-library"),
    Path("/usr/lib/R/site-library"),
    Path("/usr/lib/R/library"),
)


def localeToCharset(locale: str | None = None):
    """Guess a charset from a locale name. The default is the current locale."""
    if locale is None:
        locale = os.environ.get("LC_CTYPE") or os.environ.get("LC_ALL") or os.environ.get("LANG") or "C"
    if locale in ("C", "POSIX"):
        return "ASCII"
    parts = locale.split(".")
    # gsub("@.*$o", "", ...) never matches: $ is the end, so the o cannot follow it.
    encoding = parts[1] if len(parts) == 2 else ""
    if encoding.upper() == "UTF-8":
        encoding = "utf8"
    if encoding and encoding != "utf8":
        key = encoding.lower()
        if key in _KNOWN:
            return _KNOWN[key]
        if key.startswith("cp-") and key[3:].isdigit():
            return "CP" + key[3:]
        if key == "euc" and len(parts[0]) >= 3 and parts[0][2] == "_":
            language = parts[0][:2]
            return {"jp": "EUC-JP", "kr": "EUC-KR", "zh": "GB2312"}.get(language)
    language = parts[0]
    if len(language) >= 3 and language[2] == "_" and language[:2].isalpha():
        code = language[:2]
        if encoding == "utf8":
            return ["UTF-8", _guess(code)]
        return _guess(code)
    if encoding == "utf8":
        return "UTF-8"
    return None


def osVersion() -> str:
    """The operating-system string R stores in ``osVersion``."""
    name = os.uname().sysname
    if name != "Linux":
        raise UtilsError(f"osVersion is implemented for Linux, got {name}")
    release = Path("/etc/os-release")
    if release.exists():
        lines = release.read_text(encoding="utf-8").splitlines()
        pretty = [line for line in lines if line.startswith("PRETTY_NAME=")]
        if pretty:
            text = pretty[0][len("PRETTY_NAME=") :]
        else:
            named = [line for line in lines if line.startswith("NAME=")]
            text = named[0][len("NAME=") :] if named else "Linux (unknown distro)"
        if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
            return text[1:-1]
        return text
    system = Path("/etc/system-release")
    if system.exists():
        return system.read_text(encoding="utf-8").splitlines()[0]
    raise UtilsError("cannot determine the operating system")


def packageVersion(pkg: str, lib_loc=None) -> str:
    """The installed package version, as a string."""
    roots = [Path(path) for path in lib_loc] if lib_loc else list(_LIBRARIES)
    for root in roots:
        description = root / pkg / "DESCRIPTION"
        if description.is_file():
            for line in description.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("Version:"):
                    return line.split(":", 1)[1].strip()
    raise UtilsError(f"there is no package called \u2018{pkg}\u2019")


def _guess(language: str):
    if language in _LATIN1:
        return "ISO8859-1"
    if language in _LATIN2:
        return "ISO8859-2"
    special = {
        "mt": "ISO8859-3",
        "mk": "ISO8859-5",
        "ru": "ISO8859-5",
        "ar": "ISO8859-6",
        "el": "ISO8859-7",
        "he": "ISO8859-8",
        "iw": "ISO8859-8",
        "yi": "ISO8859-8",
        "tr": "ISO8859-9",
        "lg": "ISO8859-10",
        "lt": "ISO8859-13",
        "lv": "ISO8859-13",
        "mi": "ISO8859-13",
        "cy": "ISO8859-14",
        "uk": "KOI8-U",
        "ja": "EUC-JP",
        "ko": "EUC-KR",
        "th": "TIS-620",
        "tg": "KOI8-T",
        "ka": "GEORGIAN-PS",
        "kk": "PT154",
    }
    return special.get(language)
