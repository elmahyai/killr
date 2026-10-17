"""S3 generics for a remote package name, sha, metadata, and download.

``local_remote`` and ``cran_remote`` are built here. ``github_remote`` is
imported from ``remotes.github_remote`` and is not redefined.
"""

from __future__ import annotations

import base64
import gzip
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import warnings

from remotes.add_metadata import _read_dcf
from remotes.github_remote import github_remote

__all__ = [
    "cran_remote",
    "github_remote",
    "local_remote",
    "remote_download",
    "remote_metadata",
    "remote_package_name",
    "remote_sha",
]

_SCHEME = re.compile(r"^[A-Za-z]+://")
_ALREADY_ENCODED = re.compile(r"%[0-9A-Fa-f]{2}")
_SHA_FIELD = re.compile(r'"sha"\s*:\s*"(\w+)"')
_TAG_LINE = re.compile(r"^([^ \t][^:]*):(.*)$", re.DOTALL)
_BLANK_LINE = re.compile(r"^[ \f\r\t\v]*$")
_LEADING_SPACE = re.compile(r"^[ \f\n\r\t\v]*")
_POSIX_SPACE = " \t\n\v\f\r"
_NOT_FOUND = object()

_UNRESERVED = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._~-"
# URLencode(reserved = FALSE) also leaves RFC 3986 reserved characters,
# plus the brackets the R character class keeps.
_UNRESERVED_OR_RESERVED = "][!$&'()*+,;=:/?@#" + _UNRESERVED


class LocalRemote:
    """A remote with class names local_remote and remote."""

    def __init__(self, path, subdir):
        self.path = path
        self.subdir = subdir
        self.classes = ("local_remote", "remote")


class CranRemote:
    """A remote with class names cran_remote and remote."""

    def __init__(self, name, repos, pkg_type):
        self.name = name
        self.repos = repos
        self.pkg_type = pkg_type
        self.classes = ("cran_remote", "remote")


def normalize_path(path) -> str:
    """R ``normalizePath`` with the default ``mustWork = NA``.

    An existing path is ``realpath``. A missing path warns and is returned
    after ``path.expand``, so ``..`` in a missing path stays in the text.
    """

    expanded = os.path.expanduser(os.fspath(path))
    if expanded != "" and os.path.exists(expanded):
        return os.path.realpath(expanded)
    warnings.warn(
        f'path[1]="{expanded}": No such file or directory',
        RuntimeWarning,
        stacklevel=2,
    )
    return expanded


def local_remote(path, subdir=None, *_args, **_kwargs):
    """Build a local_remote.

    ``path`` is stored with ``normalizePath``. ``subdir`` defaults to None.
    Further arguments are accepted and ignored, as ``branch`` and ``args`` are.
    """

    return LocalRemote(normalize_path(path), subdir)


def _fix_repositories(repos):
    """Replace ``@CRAN@`` with the cloud mirror.

    ``download_url`` adds ``https://`` when the download method is secure.
    This R build has libcurl, so the mirror is ``https://cloud.r-project.org``.
    """

    cloud = "https://cloud.r-project.org"
    if repos is None:
        return None
    if isinstance(repos, str):
        return cloud if repos == "@CRAN@" else repos
    if isinstance(repos, dict):
        return {key: (cloud if value == "@CRAN@" else value) for key, value in repos.items()}
    values = [cloud if value == "@CRAN@" else value for value in repos]
    return values


def cran_remote(name, repos, type, **_kwargs):
    """Build a cran_remote.

    ``repos`` is passed through ``fix_repositories``. ``type`` is stored as
    ``pkg_type``, which is the field ``remote_sha`` reads.
    """

    return CranRemote(name, _fix_repositories(repos), type)


def _class_label(remote) -> str:
    classes = getattr(remote, "classes", None)
    if not classes:
        return type(remote).__name__
    names = tuple(classes)
    if len(names) == 1:
        return str(names[0])
    inner = ", ".join(f"'{name}'" for name in names)
    return f"c({inner})"


def _no_method(generic: str, remote) -> None:
    label = _class_label(remote)
    raise RuntimeError(
        f"no applicable method for '{generic}' applied to an object of class \"{label}\""
    )


def _dispatch(remote, methods):
    classes = getattr(remote, "classes", None)
    if not classes:
        return None
    for name in classes:
        method = methods.get(name)
        if method is not None:
            return method
    return None


def _urlencode(text, reserved: bool = False) -> str:
    """R ``URLencode``.

    ``reserved = TRUE`` encodes every byte outside the unreserved set.
    ``reserved = FALSE`` also leaves reserved characters unencoded.
    A string that already contains ``%`` plus two hex digits is returned
    unchanged, which is ``repeated = FALSE``.
    """

    if text is None:
        return ""
    raw_text = os.fspath(text) if not isinstance(text, str) else text
    if _ALREADY_ENCODED.search(raw_text):
        return raw_text
    allowed = _UNRESERVED if reserved else _UNRESERVED_OR_RESERVED
    pieces: list[str] = []
    for character in raw_text:
        encoded = character.encode("utf-8")
        if len(encoded) == 1 and character in allowed:
            pieces.append(character)
            continue
        for byte in encoded:
            pieces.append(f"%{byte:02X}")
    return "".join(pieces)


def _build_url(host, *parts) -> str:
    """``build_url``: ``file.path`` drops NULL, then ``download_url``.

    A host with no scheme gets ``https://``. ``c()`` drops NULL before
    ``file.path``, so a missing component is omitted rather than pasted.
    """

    pieces: list[str] = []
    if host is not None:
        pieces.append(os.fspath(host))
    for part in parts:
        if part is None:
            continue
        pieces.append(os.fspath(part))
    url = "/".join(pieces)
    if _SCHEME.match(url):
        return url
    return "https://" + url


def _env_auth_token():
    """GITHUB_PAT, then GITHUB_TOKEN, when the string is non-empty.

    The git credential store and the bundled CI token are not read.
    """

    for name in ("GITHUB_PAT", "GITHUB_TOKEN"):
        pat = os.environ.get(name)
        if isinstance(pat, str) and len(pat) > 0:
            return pat
    return None


def _request(url: str, auth_token):
    headers = {"User-Agent": "remotes"}
    if auth_token is not None:
        headers["Authorization"] = f"token {auth_token}"
    return urllib.request.Request(url, headers=headers)


def _read_url(url: str, auth_token=None) -> bytes:
    """Download ``url``. A failure is ``Cannot download file from``.

    That is ``download()`` when ``download.file`` returns a non-zero status.
    The non-curl GitHub path does not raise ``http_422``.
    """

    request = _request(url, auth_token)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Cannot download file from {url}") from exc


def _download_to(path: str, url: str, auth_token=None) -> str:
    payload = _read_url(url, auth_token)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(payload)
    return path


def _split_lines(text: str) -> list[str]:
    if text == "":
        return []
    lines = re.split(r"\r\n|\n|\r", text)
    if lines and lines[-1] == "" and text[-1] in "\n\r":
        lines.pop()
    return lines


def _trim_ws(value):
    """Strip POSIX space from both ends. NA stays missing."""

    if value is None:
        return None
    return str(value).strip(_POSIX_SPACE)


def _field_value(rest: str) -> str:
    return _LEADING_SPACE.sub("", rest, count=1)


def _find_version(text: str, name: str):
    """First DCF record whose Package field is ``name``.

    The return is the trimmed Version, None when that record has no Version,
    or a sentinel when the name is absent. ``read.dcf`` separates records
    with a blank line.
    """

    package = None
    version = None
    last = None
    seen = False

    def close():
        nonlocal package, version, last, seen
        if package == name and not seen:
            seen = True
            found = _trim_ws(version)
        else:
            found = _NOT_FOUND
        package = None
        version = None
        last = None
        return found

    found = _NOT_FOUND
    for line in _split_lines(text):
        if _BLANK_LINE.fullmatch(line):
            found = close()
            if found is not _NOT_FOUND:
                return found
            continue
        if line[:1] in " \t":
            if last == "Package" and package is not None:
                package = package + "\n" + line
            elif last == "Version" and version is not None:
                version = version + "\n" + line
            continue
        match = _TAG_LINE.match(line)
        if match is None:
            continue
        tag = match.group(1)
        value = _field_value(match.group(2))
        last = tag
        if tag == "Package":
            package = value
        elif tag == "Version":
            version = value
    found = close()
    if found is _NOT_FOUND:
        return _NOT_FOUND
    return found


def _r_short_version() -> str:
    """``paste(major, first minor component, sep = ".")`` from base."""

    description = "/usr/lib/R/library/base/DESCRIPTION"
    version = "4.5.0"
    if os.path.isfile(description):
        for line in _split_lines(open(description, encoding="utf-8").read()):
            if line.startswith("Version:"):
                version = _field_value(line.split(":", 1)[1])
                break
    parts = version.split(".")
    minor = parts[1] if len(parts) > 1 else "0"
    return f"{parts[0]}.{minor}"


def _platform_pkg_type() -> str:
    if sys.platform.startswith("win"):
        return "win.binary"
    if sys.platform == "darwin":
        return "mac.binary"
    return "source"


def _resolve_pkg_type(type_name: str) -> str:
    if type_name == "both":
        return "source"
    if type_name == "binary":
        return _platform_pkg_type()
    return type_name


def _repo_urls(repos) -> list[str]:
    if repos is None:
        return []
    if isinstance(repos, str):
        return [repos]
    if isinstance(repos, dict):
        return [os.fspath(value) for value in repos.values()]
    return [os.fspath(value) for value in repos]


def _contrib_urls(repos, type_name) -> list[str]:
    """``utils::contrib.url`` for one repository vector and package type."""

    if not isinstance(type_name, str):
        raise RuntimeError("'type' must be a character string")
    resolved = _resolve_pkg_type(type_name)
    urls = _repo_urls(repos)
    if "@CRAN@" in urls:
        raise RuntimeError("trying to use CRAN without setting a mirror")
    version = _r_short_version()
    mac_path = "macosx"
    if resolved.startswith("mac.binary."):
        mac_path = "macosx/" + resolved[11:]
        resolved = "mac.binary"
    built: list[str] = []
    for repo in urls:
        base = repo[:-1] if repo.endswith("/") else repo
        if resolved == "source":
            built.append(f"{base}/src/contrib")
        elif resolved == "mac.binary":
            built.append(f"{base}/bin/{mac_path}/contrib/{version}")
        elif resolved == "win.binary":
            built.append(f"{base}/bin/windows/contrib/{version}")
        else:
            raise RuntimeError("invalid 'type'")
    unique: list[str] = []
    seen: set[str] = set()
    for url in built:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def _fetch_packages(contriburl: str) -> str | None:
    """Read the text PACKAGES index. ``.gz`` is tried, then the plain file.

    ``available.packages`` prefers ``PACKAGES.rds``. That file is R's RDS
    serialization, so the text index is fetched instead. A failure warns
    and returns None, and the next repository is tried.
    """

    last = "unable to access index"
    for name in ("PACKAGES.gz", "PACKAGES"):
        url = f"{contriburl}/{name}"
        try:
            payload = _read_url(url)
        except RuntimeError as exc:
            last = str(exc)
            continue
        if payload[:2] == b"\x1f\x8b":
            try:
                payload = gzip.decompress(payload)
            except OSError as exc:
                last = str(exc)
                continue
        return payload.decode("utf-8", errors="surrogateescape")
    warnings.warn(
        f"unable to access index for repository {contriburl}:\n  {last}",
        RuntimeWarning,
        stacklevel=2,
    )
    return None


def _cran_version(name, repos, pkg_type):
    """Version of ``name`` from the first repository that lists it."""

    for url in _contrib_urls(repos, pkg_type):
        text = _fetch_packages(url)
        if text is None:
            continue
        found = _find_version(text, name)
        if found is _NOT_FOUND:
            continue
        return found
    return None


def _lib_paths() -> list[str]:
    """Library directories the comparison session searches.

    The session prepends ``~/R/library`` and then uses ``.libPaths()``.
    """

    home = os.path.expanduser("~")
    short = _r_short_version()
    candidates = [
        os.path.join(home, "R", "library"),
        os.path.join(home, "R", "x86_64-pc-linux-gnu-library", short),
        "/usr/local/lib/R/site-library",
        "/usr/lib/R/site-library",
        "/usr/lib/R/library",
    ]
    r_libs = os.environ.get("R_LIBS")
    if r_libs:
        candidates = [path for path in r_libs.split(os.pathsep) if path] + candidates
    unique: list[str] = []
    seen: set[str] = set()
    for path in candidates:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def _installed_package_name(repo):
    """``packageDescription(repo, fields = "Package")`` when the package exists.

    A missing package is None, which is the NA that ``!is.na`` rejects.
    """

    if not isinstance(repo, str) or repo == "":
        return None
    for lib in _lib_paths():
        description = os.path.join(lib, repo, "DESCRIPTION")
        if not os.path.isfile(description):
            continue
        try:
            fields = _read_dcf(description)
        except (OSError, ValueError):
            continue
        name = fields.get("Package")
        if name:
            return name
    return None


def _github_description(remote):
    """DESCRIPTION text from the contents API, the non-curl branch.

    The body is JSON. ``content`` is base64. ``json.loads`` turns ``\\n``
    into newlines and ``b64decode`` ignores that whitespace. The R parser
    leaves the backslash and ``n`` in the text and then deletes that pair.
    """

    pat = remote.auth_token if remote.auth_token is not None else _env_auth_token()
    parts = ["repos", remote.username, remote.repo, "contents"]
    if remote.subdir is not None:
        parts.append(_urlencode(remote.subdir, reserved=False))
    parts.append("DESCRIPTION")
    url = _build_url(remote.host, *parts)
    ref = "" if remote.ref is None else remote.ref
    url = url + "?ref=" + _urlencode(ref, reserved=False)
    payload = _read_url(url, pat)
    parsed = json.loads(payload.decode("utf-8"))
    content = parsed.get("content") if isinstance(parsed, dict) else None
    if not isinstance(content, str):
        return None
    text = base64.b64decode(content).decode("utf-8", errors="surrogateescape")
    temporary = tempfile.NamedTemporaryFile(delete=False)
    try:
        temporary.write(text.encode("utf-8", errors="surrogateescape"))
        temporary.close()
        return _read_dcf(temporary.name)
    finally:
        os.unlink(temporary.name)


def _get_json_sha(text: str):
    """``get_json_sha``: the first ``"sha"`` string, else the parsed field.

    ``\\w+`` is the capture. A missing field is NA, returned here as None.
    """

    match = _SHA_FIELD.search(text)
    if match is not None:
        return match.group(1)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    sha = parsed.get("sha")
    if sha is None:
        return None
    return sha


def _git_extract_sha1_tar(bundle):
    """SHA from the pax comment after the 512-byte tar header.

    ``gzcon`` reads a gzip member, and a file that is not gzip is read as
    itself. The next 51 bytes are ``52 comment=`` plus the 40-character SHA.
    Anything else is NULL.
    """

    path = os.fspath(bundle)
    try:
        with open(path, "rb") as handle:
            magic = handle.read(2)
            handle.seek(0)
            if magic == b"\x1f\x8b":
                with gzip.GzipFile(fileobj=handle) as compressed:
                    raw = compressed.read(0x200 + 0x33)
            else:
                raw = handle.read(0x200 + 0x33)
    except OSError:
        return None
    chunk = raw[0x200:0x200 + 0x33]
    text = chunk.decode("latin1")
    prefix = "52 comment="
    if text.startswith(prefix):
        return text[len(prefix):]
    return None


def _first_dir_entry(bundle: str):
    """``dir(bundle, full.names = TRUE)[1]``.

    Names starting with ``.`` are omitted, and the rest are sorted.
    An empty listing is NA.
    """

    names = sorted(
        name
        for name in os.listdir(bundle)
        if name not in (".", "..") and not name.startswith(".")
    )
    if not names:
        warnings.warn("subscript out of bounds", RuntimeWarning, stacklevel=3)
        return None
    return os.path.join(bundle, names[0])


def _download_local(x, quiet=False):
    """Copy ``x.path`` into a new temporary directory and return that copy.

    ``file.copy`` of a directory creates ``bundle/<basename>``. The return
    value is the first name inside ``bundle``, which is that copy.
    """

    del quiet
    bundle = tempfile.mkdtemp()
    dest = os.path.join(bundle, os.path.basename(os.path.normpath(x.path)))
    try:
        if os.path.isdir(x.path):
            shutil.copytree(x.path, dest)
        elif os.path.exists(x.path):
            shutil.copy2(x.path, dest)
        else:
            raise OSError(x.path)
    except OSError as exc:
        raise RuntimeError(f"Could not copy `{x.path}` to `{bundle}`") from exc
    return _first_dir_entry(bundle)


def _download_github(x, quiet=False):
    """Save ``repos/{user}/{repo}/tarball/{ref}`` to a ``.tar.gz`` file.

    ``ref`` is encoded with ``reserved = TRUE``. The token is the remote's
    ``auth_token`` and is not filled from the environment.
    """

    if not quiet:
        print(
            f"Downloading GitHub repo {x.username}/{x.repo}@{x.ref}",
            file=sys.stderr,
        )
    handle = tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False)
    dest = handle.name
    handle.close()
    ref = _urlencode("" if x.ref is None else x.ref, reserved=True)
    root = _build_url(x.host, "repos", x.username, x.repo)
    url = f"{root}/tarball/{ref}"
    return _download_to(dest, url, auth_token=x.auth_token)


def _metadata_local(x, bundle=None, source=None, sha=None):
    del bundle, source, sha
    return {
        "RemoteType": "local",
        "RemoteUrl": x.path,
        "RemoteSubdir": x.subdir,
    }


def _metadata_github(x, bundle=None, source=None, sha=None):
    """Remote* and Github* fields.

    An explicit sha is stored on both ``RemoteSha`` and ``GithubSHA1``.
    A bundle replaces that sha with the tar comment. A length-1 NA becomes
    NULL, which is None here, the same as an omitted sha.
    """

    del source
    if bundle is not None:
        sha = _git_extract_sha1_tar(bundle)
    elif sha is None:
        sha = None
    return {
        "RemoteType": "github",
        "RemoteHost": x.host,
        "RemotePackage": x.package,
        "RemoteRepo": x.repo,
        "RemoteUsername": x.username,
        "RemoteRef": x.ref,
        "RemoteSha": sha,
        "RemoteSubdir": x.subdir,
        "GithubRepo": x.repo,
        "GithubUsername": x.username,
        "GithubRef": x.ref,
        "GithubSHA1": sha,
        "GithubSubdir": x.subdir,
    }


def _tarball_package_name(path: str) -> str:
    """Text of the file name before the first underscore."""

    return re.sub(r"_.*\Z", "", os.path.basename(path), count=1)


def _package_name_local(remote, *_args, **_kwargs):
    if not os.path.isdir(remote.path):
        return _tarball_package_name(remote.path)
    fields = _read_dcf(os.path.join(remote.path, "DESCRIPTION"))
    return fields.get("Package")


def _package_name_cran(remote, *_args, **_kwargs):
    return remote.name


def _package_name_github(remote, *_args, use_local=True, use_curl=False, **_kwargs):
    """Return ``package`` when it is already set.

    That branch does not touch the network. ``use_curl`` is ignored: the
    DESCRIPTION lookup uses the contents API through ``urllib``.
    """

    del use_curl
    if remote.package is not None:
        return remote.package
    if use_local is True:
        local_name = _installed_package_name(remote.repo)
        if local_name is not None:
            return local_name
    fields = _github_description(remote)
    if fields is None:
        return None
    return fields.get("Package")


def _package_name_default(remote, *_args, **_kwargs):
    return getattr(remote, "repo", None)


def _sha_local(remote, *_args, **_kwargs):
    if not os.path.isdir(remote.path):
        return None
    fields = _read_dcf(os.path.join(remote.path, "DESCRIPTION"))
    return fields.get("Version")


def _sha_cran(remote, *_args, **_kwargs):
    return _cran_version(remote.name, remote.repos, remote.pkg_type)


def _sha_github(remote, *_args, use_curl=False, **_kwargs):
    """Commit SHA from the JSON body, the non-curl ``github_commit`` path.

    The URL is ``repos/{user}/{repo}/commits/{ref}``. The curl path would
    send ``Accept: application/vnd.github.v3.sha`` and return the raw body.
    This path reads the ``sha`` field. ``use_curl`` is ignored.
    """

    del use_curl
    pat = remote.auth_token if remote.auth_token is not None else _env_auth_token()
    ref = _urlencode("" if remote.ref is None else remote.ref, reserved=True)
    url = _build_url(
        remote.host,
        "repos",
        remote.username,
        remote.repo,
        "commits",
        ref,
    )
    payload = _read_url(url, pat)
    text = payload.decode("utf-8", errors="surrogateescape")
    return _get_json_sha(text)


def _sha_default(remote, *_args, **_kwargs):
    """``NA_character_`` is None."""

    del remote
    return None


_DOWNLOAD = {
    "local_remote": _download_local,
    "github_remote": _download_github,
}

_METADATA = {
    "local_remote": _metadata_local,
    "github_remote": _metadata_github,
}

_PACKAGE_NAME = {
    "local_remote": _package_name_local,
    "cran_remote": _package_name_cran,
    "github_remote": _package_name_github,
}

_SHA = {
    "local_remote": _sha_local,
    "cran_remote": _sha_cran,
    "github_remote": _sha_github,
}


def remote_download(x, quiet=False):
    """Download the source bundle for a remote."""

    method = _dispatch(x, _DOWNLOAD)
    if method is None:
        _no_method("remote_download", x)
    return method(x, quiet=quiet)


def remote_metadata(x, bundle=None, source=None, sha=None):
    """Metadata fields recorded for a remote."""

    method = _dispatch(x, _METADATA)
    if method is None:
        _no_method("remote_metadata", x)
    return method(x, bundle=bundle, source=source, sha=sha)


def remote_package_name(remote, *args, **kwargs):
    """Package name for a remote. The default method returns ``repo``."""

    method = _dispatch(remote, _PACKAGE_NAME)
    if method is None:
        method = _package_name_default
    return method(remote, *args, **kwargs)


def remote_sha(remote, *args, **kwargs):
    """SHA or version for a remote. The default method returns None."""

    method = _dispatch(remote, _SHA)
    if method is None:
        method = _sha_default
    return method(remote, *args, **kwargs)
