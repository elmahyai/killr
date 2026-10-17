"""Bioconductor version and repository URLs from remotes 2.5.0.

The config.yaml download used when the builtin map has no entry lives in
this module. It is not a download helper for the rest of remotes.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass

# Session stand-in for getOption("BioC_mirror"). A stored value wins over
# R_BIOC_MIRROR, which itself defaults to https://bioconductor.org.
options: dict[str, str] = {}

_VERSION_RE = re.compile(r"(?:[0-9]+[.-]){1,}[0-9]+")
_CONFIG_URL = "https://bioconductor.org/config.yaml"
_MIRROR = "https://bioconductor.org"

_yaml_lines: list[str] | None = None
_release: _Version | None = None
_devel: _Version | None = None
_rows: list[_Row] | None = None
_r_version_text: str | None = None


@dataclass(frozen=True, slots=True)
class _Version:
    """R package_version: numeric components, trailing zeros equal."""

    parts: tuple[int, ...]

    def __str__(self) -> str:
        return ".".join(str(part) for part in self.parts)

    def _aligned(self, other: _Version) -> tuple[tuple[int, ...], tuple[int, ...]]:
        width = max(len(self.parts), len(other.parts))
        left = self.parts + (0,) * (width - len(self.parts))
        right = other.parts + (0,) * (width - len(other.parts))
        return left, right

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _Version):
            return NotImplemented
        left, right = self._aligned(other)
        return left == right

    def __hash__(self) -> int:
        parts = self.parts
        while len(parts) > 1 and parts[-1] == 0:
            parts = parts[:-1]
        return hash(parts)

    def __lt__(self, other: _Version) -> bool:
        left, right = self._aligned(other)
        return left < right

    def __le__(self, other: _Version) -> bool:
        left, right = self._aligned(other)
        return left <= right

    def __gt__(self, other: _Version) -> bool:
        left, right = self._aligned(other)
        return left > right

    def __ge__(self, other: _Version) -> bool:
        left, right = self._aligned(other)
        return left >= right


@dataclass(frozen=True, slots=True)
class _Row:
    bioc: _Version
    r: _Version
    status: str


def _invalid_version(text: str) -> ValueError:
    return ValueError(f"invalid version specification \u2018{text}\u2019")


def _package_version(value: str | _Version) -> _Version:
    if isinstance(value, _Version):
        return value
    if not isinstance(value, str) or _VERSION_RE.fullmatch(value) is None:
        shown = value if isinstance(value, str) else str(value)
        raise _invalid_version(shown)
    parts = tuple(int(piece) for piece in re.split(r"[.-]", value))
    return _Version(parts)


def _minor_name(r_version: str) -> str:
    """First two components, the way package_version(x)[, 1:2] prints."""

    version = _package_version(r_version)
    if len(version.parts) < 2:
        raise _invalid_version(r_version)
    return str(_Version(version.parts[:2]))


# Names are the minor strings. 2.15 is 2.11 and 3.0 is 2.13: those gaps are
# in the installed map. R 3.7, 3.8, and 3.9 are absent on purpose.
_BUILTIN_PAIRS = (
    ("2.1", "1.6"),
    ("2.2", "1.7"),
    ("2.3", "1.8"),
    ("2.4", "1.9"),
    ("2.5", "2.0"),
    ("2.6", "2.1"),
    ("2.7", "2.2"),
    ("2.8", "2.3"),
    ("2.9", "2.4"),
    ("2.10", "2.5"),
    ("2.11", "2.6"),
    ("2.12", "2.7"),
    ("2.13", "2.8"),
    ("2.14", "2.9"),
    ("2.15", "2.11"),
    ("3.0", "2.13"),
    ("3.1", "3.0"),
    ("3.2", "3.2"),
    ("3.3", "3.4"),
    ("3.4", "3.6"),
    ("3.5", "3.8"),
    ("3.6", "3.10"),
    ("4.0", "3.12"),
    ("4.1", "3.14"),
    ("4.2", "3.16"),
    ("4.3", "3.17"),
    ("4.4", "3.18"),
)
_BUILTIN = {minor: _package_version(bioc) for minor, bioc in _BUILTIN_PAIRS}


def _header_candidates() -> list[str]:
    found = [
        "/usr/share/R/include/Rversion.h",
        "/usr/include/R/Rversion.h",
        "/usr/include/Rversion.h",
    ]
    rscript = shutil.which("Rscript")
    if rscript:
        prefix = os.path.dirname(os.path.dirname(os.path.realpath(rscript)))
        found.insert(0, os.path.join(prefix, "include", "Rversion.h"))
        found.insert(0, os.path.join(prefix, "lib", "R", "include", "Rversion.h"))
        found.insert(0, os.path.join(prefix, "share", "R", "include", "Rversion.h"))
    return found


def _current_r_version() -> str:
    """getRversion(): paste0(R.version$major, '.', R.version$minor)."""

    global _r_version_text
    if _r_version_text is not None:
        return _r_version_text
    header = None
    for path in _header_candidates():
        try:
            with open(path, encoding="utf-8") as handle:
                header = handle.read()
        except OSError:
            continue
        break
    if header is not None:
        major = re.search(r'#define\s+R_MAJOR\s+"([^"]*)"', header)
        minor = re.search(r'#define\s+R_MINOR\s+"([^"]*)"', header)
        if major is not None and minor is not None:
            _r_version_text = f"{major.group(1)}.{minor.group(1)}"
            return _r_version_text
    completed = subprocess.run(
        ["Rscript", "-e", "cat(as.character(getRversion()))"],
        check=True,
        capture_output=True,
        text=True,
    )
    _r_version_text = completed.stdout.strip()
    return _r_version_text


def _read_url(url: str) -> list[str]:
    request = urllib.request.Request(url, headers={"User-Agent": "R"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Failed to download `{url}`") from exc
    if not payload:
        raise RuntimeError(f"Failed to download `{url}`")
    return payload.decode("utf-8").splitlines()


def _config_url() -> str:
    return os.environ.get("R_BIOC_CONFIG_URL", _CONFIG_URL)


def _yaml_config() -> list[str]:
    """Cached config.yaml lines, the closure's yaml_config."""

    global _yaml_lines
    if _yaml_lines is None:
        url = _config_url()
        try:
            downloaded = _read_url(url)
        except RuntimeError:
            downloaded = _read_url(re.sub(r"^https", "http", url, count=1))
        _yaml_lines = downloaded
    return _yaml_lines


def _labeled_version(lines: list[str], key: str) -> _Version:
    pattern = re.compile(rf'^{re.escape(key)}: "(.*)"')
    found = [pattern.sub(r"\1", line, count=1) for line in lines if pattern.search(line)]
    if len(found) != 1:
        raise ValueError(f"could not read {key} from the Bioconductor config")
    return _package_version(found[0])


def _release_version() -> _Version:
    global _release
    if _release is None:
        _release = _labeled_version(_yaml_config(), "release_version")
    return _release


def _devel_version() -> _Version:
    global _devel
    if _devel is None:
        _devel = _labeled_version(_yaml_config(), "devel_version")
    return _devel


def _unindented(lines: list[str]) -> list[int]:
    return [index for index, line in enumerate(lines) if line[:1] not in ("", " ", "\t")]


def _map_section(lines: list[str]) -> list[str]:
    groups = _unindented(lines)
    hits = [index for index, line in enumerate(lines) if "r_ver_for_bioc_ver" in line]
    start = None
    for hit in hits:
        if hit in groups:
            start = groups.index(hit)
            break
    if start is None or start + 1 >= len(groups):
        raise ValueError("cannot find r_ver_for_bioc_ver in the Bioconductor config")
    begin = groups[start] + 1
    end = groups[start + 1]
    return lines[begin:end]


def _clean_map_line(line: str) -> str:
    cleaned = re.sub(r" #.*", "", line)
    cleaned = cleaned.replace('"', "")
    return cleaned.strip(" \t\r\n\f\v")


def _shift_release_r(version: _Version) -> _Version:
    """unlist(max(r)) + 0:1, recycled to the longer length."""

    parts = version.parts
    add = (0, 1)
    width = max(len(parts), len(add))
    shifted = tuple(parts[i % len(parts)] + add[i % len(add)] for i in range(width))
    return _Version(shifted)


def _maximum(versions: list[_Version]) -> _Version:
    best = versions[0]
    for item in versions[1:]:
        if item > best:
            best = item
    return best


def _version_map() -> list[_Row]:
    global _rows
    if _rows is not None:
        return _rows
    raw = [_clean_map_line(line) for line in _map_section(_yaml_config())]
    pattern = re.compile(r"(.*): (.*)")
    bioc_text = [pattern.sub(r"\1", line, count=1) for line in raw]
    r_text = [pattern.sub(r"\2", line, count=1) for line in raw]
    bioc = [_package_version(text) for text in bioc_text]
    r_versions = [_package_version(text) for text in r_text]
    release = _release_version()
    devel = _devel_version()
    status = ["out-of-date"] * len(bioc)
    for index, item in enumerate(bioc):
        if item == release:
            status[index] = "release"
    for index, item in enumerate(bioc):
        if item == devel:
            status[index] = "devel"
    bioc.append(_maximum(bioc))
    r_versions.append(_shift_release_r(_maximum(r_versions)))
    status.append("future")
    _rows = [
        _Row(bioc=bioc_item, r=r_item, status=flag)
        for bioc_item, r_item, flag in zip(bioc, r_versions, status, strict=True)
    ]
    return _rows


def _matching(r_version: str) -> _Version:
    minor_name = _minor_name(r_version)
    builtin = _BUILTIN.get(minor_name)
    if builtin is not None:
        return builtin

    minor = _package_version(minor_name)
    hits = [row for row in _version_map() if row.r == minor]
    if len(hits) > 1:
        statuses = [row.status for row in hits]
        if "release" in statuses:
            hits = [row for row in hits if row.status == "release"]
        elif "devel" in statuses:
            hits = [row for row in hits if row.status == "devel"]
        else:
            # Several out-of-date rows share this R version. R keeps the last.
            hits = [hits[-1]]
    if hits:
        return hits[0].bioc
    if minor < _package_version("2.1"):
        raise ValueError("R version too old, cannot run Bioconductor")
    return _devel_version()


def _bioc_version(r_version: str) -> _Version:
    forced = os.environ.get("R_BIOC_VERSION", "")
    if forced:
        return _package_version(forced)
    return _matching(r_version)


def _mirror() -> str:
    mirror = os.environ.get("R_BIOC_MIRROR", _MIRROR)
    return options.get("BioC_mirror", mirror)


def _repos(bioc_ver: str) -> list[tuple[str, str]]:
    if bioc_ver == "auto":
        version = _bioc_version(_current_r_version())
    else:
        version = _package_version(bioc_ver)
    mirror = _mirror()
    bv = str(version)
    chosen: list[tuple[str, str]] = [
        ("BioCsoft", "{mirror}/packages/{bv}/bioc"),
        ("BioCann", "{mirror}/packages/{bv}/data/annotation"),
        ("BioCexp", "{mirror}/packages/{bv}/data/experiment"),
    ]
    if version >= _package_version("3.7"):
        chosen.append(("BioCworkflows", "{mirror}/packages/{bv}/workflows"))
    if version <= _package_version("3.5"):
        chosen.append(("BioCextra", "{mirror}/packages/{bv}/extra"))
    if version >= _package_version("3.12"):
        chosen.append(("BioCbooks", "{mirror}/packages/{bv}/books"))
    repos: list[tuple[str, str]] = []
    for name, template in chosen:
        url = template.replace("{bv}", bv).replace("{mirror}", mirror)
        repos.append((name, url))
    return repos


def bioc_version(r_ver: str | None = None) -> str:
    """Bioconductor version for an R version, as a dotted string.

    A non-empty ``R_BIOC_VERSION`` is returned and ``r_ver`` is ignored.
    ``None`` uses the installed R version.
    """

    if r_ver is None:
        r_ver = _current_r_version()
    return str(_bioc_version(r_ver))


def bioc_install_repos(
    r_ver: str | None = None,
    bioc_ver: str | None = None,
) -> list[tuple[str, str]]:
    """Named Bioconductor repository URLs, in R's order.

    The default ``bioc_ver`` is ``bioc_version(r_ver)``. ``"auto"`` looks up
    the current R version. Each item is a ``(name, url)`` pair.
    """

    if bioc_ver is None:
        bioc_ver = bioc_version(r_ver)
    return _repos(bioc_ver)


__all__ = ["bioc_version", "bioc_install_repos"]
