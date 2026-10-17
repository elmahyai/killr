"""Create a github_remote from a repository specification.

``parse_git_repo`` lives here. The R package does not export it.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone

from remotes.github_refs import GithubPull, GithubRelease, github_pull, github_release
from remotes.parse import parse_github_url, parse_repo_spec

_GITHUB_FORM = re.compile(r"^https://github|^git@github")
_SCHEME = re.compile(r"^[A-Za-z]+://")
_MISSING = object()


def _or_null(left, right):
    """R ``%||%``: keep the left side unless it is None.

    An empty string is kept.
    """
    if left is None:
        return right
    return left


def _env_auth_token():
    """GITHUB_PAT, then GITHUB_TOKEN, when the string is non-empty."""
    for name in ("GITHUB_PAT", "GITHUB_TOKEN"):
        pat = os.environ.get(name)
        if isinstance(pat, str) and len(pat) > 0:
            return pat
    return None


def _keep_field(value) -> bool:
    """Drop a field whose nchar is 0. Keep every non-empty value."""
    if isinstance(value, str):
        return len(value) > 0
    return True


def parse_git_repo(repo: str) -> dict:
    """Parse a GitHub URL or a shorthand repo spec.

    Fields whose nchar is 0 are removed. A remaining pull becomes
    ``github_pull(pull)`` on ``ref``. A remaining release becomes
    ``github_release()`` on ``ref``.
    """
    if _GITHUB_FORM.search(repo):
        params = parse_github_url(repo)
    else:
        params = parse_repo_spec(repo)
    kept = {key: value for key, value in params.items() if _keep_field(value)}
    if "pull" in kept:
        kept["ref"] = github_pull(kept.pop("pull"))
    if "release" in kept:
        kept["ref"] = github_release()
        del kept["release"]
    return kept


def _build_url(host, path) -> str:
    """``build_url``: join host and path, then add https:// when needed."""
    host_text = "" if host is None else str(host)
    path_text = "" if path is None else str(path).lstrip("/")
    if host_text and path_text:
        url = f"{host_text}/{path_text}"
    else:
        url = host_text or path_text
    if _SCHEME.match(url):
        return url
    return "https://" + url


def _as_r_text(value) -> str:
    """Paste a pull id the way R pastes the ``github_pull`` vector."""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, GithubPull):
        return _as_r_text(value.pull)
    if value is None:
        return "NULL"
    return str(value)


def _as_int(value):
    """``as.integer`` of one header or status. Unparseable text is missing."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(str(value))
    except ValueError:
        return None


def _format_reset(reset) -> str:
    """``format(.POSIXct(reset, tz = "UTC"), usetz = TRUE)``."""
    stamp = _as_int(reset)
    if stamp is None:
        return "NA"
    return datetime.fromtimestamp(stamp, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _github_guidance(status, remaining, url) -> str:
    """The guidance paragraph of ``github_error``."""
    if _as_int(remaining) == 0:
        if os.environ.get("TRAVIS") == "true":
            extra = "Add `GITHUB_PAT` to your travis settings as an encrypted variable."
        else:
            extra = "Use `gitcreds::gitcreds_set()` to add the token."
        return (
            "To increase your GitHub API rate limit\n"
            "  - Use `usethis::create_github_token()` to create a Personal Access Token.\n"
            f"  - {extra}"
        )
    if _as_int(status) == 404:
        found = re.search(r"repos/([^/]+)/([^/]+)/", url or "")
        if found:
            owner, repo = found.group(1), found.group(2)
            return (
                f"Did you spell the repo owner (`{owner}`) and repo name (`{repo}`) correctly?\n"
                "  - If spelling is correct, check that you have the required permissions to access the repo."
            )
        return (
            "Did you spell the repo owner and repo name correctly?\n"
            "  - If spelling is correct, check that you have the required permissions to access the repo."
        )
    return ""


def _github_error_message(status, details, headers, url) -> str:
    """``github_error`` message. A NULL detail is an empty ``%s``."""
    header_map = {str(key).lower(): value for key, value in headers.items()}
    limit = header_map.get("x-ratelimit-limit")
    remaining = header_map.get("x-ratelimit-remaining")
    guidance = _github_guidance(status, remaining, url)
    detail_text = "" if details is None else str(details)
    if _as_int(status) == 404:
        return f"HTTP error {status}.\n  {detail_text}\n\n  {guidance}"
    if limit is not None:
        reset_text = _format_reset(header_map.get("x-ratelimit-reset"))
        remaining_text = "" if remaining is None else str(remaining)
        return (
            f"HTTP error {status}.\n"
            f"  {detail_text}\n"
            "\n"
            f"  Rate limit remaining: {remaining_text}/{limit}\n"
            f"  Rate limit reset at: {reset_text}\n"
            "\n"
            f"  {guidance}"
        )
    return f"HTTP error {status}.\n  {detail_text}"


def _json_message(payload: bytes):
    """The ``message`` field. JSON null and a missing field are None."""
    parsed = json.loads(payload.decode("utf-8"))
    if isinstance(parsed, dict):
        return parsed.get("message")
    return None


def _github_get(path, host, pat):
    """GET a GitHub API path.

    ``Authorization: token {pat}`` is sent when ``pat`` is not None.
    The installed function uses the curl package. An HTTP status at or
    above 300 becomes the ``github_error`` message, including the body.
    """
    url = _build_url(host, path)
    headers = {}
    if pat is not None:
        headers["Authorization"] = f"token {pat}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read()
    except urllib.error.HTTPError as exc:
        payload = exc.read()
        try:
            details = _json_message(payload)
        except json.JSONDecodeError as err:
            raise RuntimeError(f"JSON: {err.msg}") from err
        raise RuntimeError(
            _github_error_message(exc.code, details, exc.headers, url)
        ) from None
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"cannot open URL '{url}'") from exc
    try:
        return json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"JSON: {exc.msg}") from exc


def _stop_with_message(prefix: str, message) -> None:
    """``stop(prefix, "\\n", message)``. A NULL message adds only the newline."""
    if message is None:
        raise RuntimeError(prefix + "\n")
    raise RuntimeError(prefix + "\n" + str(message))


def _resolve_pull(x, params, host, auth_token):
    number = x.pull
    username = params.get("username")
    repo = params.get("repo")
    path = f"repos/{username}/{repo}/pulls/{_as_r_text(number)}"
    try:
        response = _github_get(path, host, auth_token)
    except RuntimeError as exc:
        _stop_with_message(
            f"Cannot find GitHub pull request {username}/{repo}#{_as_r_text(number)}",
            str(exc),
        )
    head = response.get("head") if isinstance(response, dict) else None
    if head is None:
        message = response.get("message") if isinstance(response, dict) else None
        _stop_with_message(
            f"Cannot find GitHub pull request {username}/{repo}#{_as_r_text(number)}",
            message,
        )
    user = head.get("user") if isinstance(head, dict) else None
    login = user.get("login") if isinstance(user, dict) else None
    ref = head.get("ref") if isinstance(head, dict) else None
    resolved = dict(params)
    resolved["username"] = login
    resolved["ref"] = ref
    return resolved


def _resolve_release(params, host, auth_token):
    username = params.get("username")
    repo = params.get("repo")
    path = f"repos/{username}/{repo}/releases"
    try:
        response = _github_get(path, host, auth_token)
    except RuntimeError as exc:
        _stop_with_message(f"Cannot find repo {username}/{repo}.", str(exc))
    message = response.get("message") if isinstance(response, dict) else None
    if message is not None:
        _stop_with_message(f"Cannot find repo {username}/{repo}.", message)
    if not isinstance(response, (list, dict)) or len(response) == 0:
        raise RuntimeError(f"No releases found for repo {username}/{repo}.")
    if isinstance(response, list):
        first = response[0]
    else:
        first = next(iter(response.values()))
    tag = first.get("tag_name") if isinstance(first, dict) else None
    resolved = dict(params)
    resolved["ref"] = tag
    return resolved


def github_resolve_ref(x, params, host="api.github.com", auth_token=None, **_ignored):
    """Resolve ``x`` onto ``params["ref"]``.

    A string is stored as that string. None becomes ``"HEAD"``.
    A github_pull GETs ``/repos/{username}/{repo}/pulls/{number}`` and
    replaces ``username`` and ``ref`` from ``head``. A github_release GETs
    ``/repos/{username}/{repo}/releases`` and stores the first ``tag_name``.
    """
    if isinstance(x, GithubPull):
        return _resolve_pull(x, params, host, auth_token)
    if isinstance(x, GithubRelease):
        return _resolve_release(params, host, auth_token)
    resolved = dict(params)
    resolved["ref"] = "HEAD" if x is None else x
    return resolved


class GithubRemote:
    """A remote with class names github_remote and remote."""

    def __init__(self, host, package, repo, subdir, username, ref, sha, auth_token):
        self.host = host
        self.package = package
        self.repo = repo
        self.subdir = subdir
        self.username = username
        self.ref = ref
        self.sha = sha
        self.auth_token = auth_token
        self.classes = ("github_remote", "remote")


def github_remote(
    repo,
    ref="HEAD",
    subdir=None,
    auth_token=_MISSING,
    sha=None,
    host="api.github.com",
    *_args,
    **_kwargs,
):
    """Build a github_remote. Extra arguments are accepted and ignored.

    The default ``auth_token`` is ``GITHUB_PAT``, then ``GITHUB_TOKEN``,
    when that string is non-empty. If neither is set, the default is None.
    An explicit None stays None. The git credential store is not read.
    """
    if auth_token is _MISSING:
        auth_token = _env_auth_token()
    meta = parse_git_repo(repo)
    meta = github_resolve_ref(
        _or_null(meta.get("ref"), ref),
        meta,
        host=host,
        auth_token=auth_token,
    )
    return GithubRemote(
        host=host,
        package=meta.get("package"),
        repo=meta.get("repo"),
        subdir=_or_null(meta.get("subdir"), subdir),
        username=meta.get("username"),
        ref=meta.get("ref"),
        sha=sha,
        auth_token=auth_token,
    )
