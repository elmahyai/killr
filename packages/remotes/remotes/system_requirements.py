"""Query the Posit Package Manager system-requirements API."""

from __future__ import annotations

import math
import re
import shutil
import subprocess
from os import environ, path as ospath

_DEFAULT_RSPM = "https://packagemanager.posit.co"
_DEFAULT_REPO_ID = "1"

# The commented debian and windows entries in the R source are not returned.
_OS_VERSIONS: dict[str, tuple[str, ...]] = {
    "ubuntu": ("14.04", "16.04", "18.04", "20.04", "22.04"),
    "centos": ("6", "7", "8"),
    "redhat": ("6", "7", "8"),
    "opensuse": ("42.3", "15.0"),
    "sle": ("12.3", "15.0"),
}

_OS_NAMES = tuple(_OS_VERSIONS)

_MISSING_OS = "If os_release is missing, os must consist of name and release."
_MISSING_CURL = "`curl` must be on the `PATH`."
_CURL_FAILED = "error in running command"

# remotes' tokenizer. Escapes stay in the token text; they are not interpreted.
_CNTRL = r"\x00-\x1f\x7f"
_TOKEN_RE = re.compile(
    rf'"(?:[^{_CNTRL}"\\]*(?:\\(?:[^{_CNTRL}u]|u[0-9a-fA-F]{{4}})[^{_CNTRL}"\\]*)*)"'
    r"|-?(?:0|[1-9][0-9]*)(?:[.][0-9]*)?(?:[eE][+-]?[0-9]*)?"
    r"|null|false|true"
    r"|\s+"
    r"|.",
)


def system_requirements(
    os: str,
    os_release: str | None = None,
    path: str = ".",
    package: str | list[str] | tuple[str, ...] | None = None,
    curl: str | None = None,
) -> list[str]:
    """Return install commands for ``os`` / ``os_release``.

    ``os_release=None`` splits ``os`` on ``-`` into a name and a release.
    A unique prefix is accepted, as in ``match.arg``. An empty ``curl``
    is refused after that check. ``package=None`` posts the DESCRIPTION
    file; a package name uses the query form.
    """

    os_name, release = _resolve_os(os, os_release)
    if curl is None:
        curl = shutil.which("curl") or ""
    if curl == "":
        raise RuntimeError(_MISSING_CURL)

    repo = _repo_url()
    if package is not None:
        names = _package_names(package)
        url = (
            f"{repo}/sysreqs?all=false&pkgname={names}"
            f"&distribution={os_name}&release={release}"
        )
        body = _curl_stdout(curl, ["--silent", "-L", _sh_quote(url)])
        return _commands(_parse_json(body), "requirements", ("requirements",))

    description = _description_path(path)
    if not ospath.exists(description):
        raise RuntimeError(f"`{path}` must contain a package.")
    url = (
        f"{repo}/sysreqs?distribution={os_name}&release={release}&suggests=true"
    )
    body = _curl_stdout(
        curl,
        [
            "--silent",
            "-L",
            "--data-binary",
            _sh_quote("@" + description),
            _sh_quote(url),
        ],
    )
    return _commands(_parse_json(body), "dependencies", ())


def _resolve_os(os_name: object, os_release: object) -> tuple[str, str]:
    if os_release is None:
        if not isinstance(os_name, str):
            raise RuntimeError(_MISSING_OS)
        parts = os_name.split("-")
        # strsplit drops one trailing empty piece and keeps the rest.
        if parts and parts[-1] == "":
            del parts[-1]
        if len(parts) != 2:
            raise RuntimeError(_MISSING_OS)
        os_name, os_release = parts[0], parts[1]
    name = _match_arg(os_name, _OS_NAMES)
    release = _match_arg(os_release, _OS_VERSIONS[name])
    return name, release


def _match_arg(arg: object, choices: tuple[str, ...]) -> str:
    """``match.arg`` with ``several.ok = FALSE`` and ``pmatch``."""

    if arg is None:
        return choices[0]
    if not isinstance(arg, str):
        raise RuntimeError("'arg' must be NULL or a character vector")
    # An empty string matches nothing, even though it is a prefix of everything.
    if arg == "":
        _match_arg_fail(choices)
    exact = [choice for choice in choices if choice == arg]
    if exact:
        return exact[0]
    partial = [choice for choice in choices if choice.startswith(arg)]
    if len(partial) == 1:
        return partial[0]
    _match_arg_fail(choices)


def _match_arg_fail(choices: tuple[str, ...]) -> None:
    quoted = ", ".join(f"\u201c{choice}\u201d" for choice in choices)
    raise RuntimeError(f"'arg' should be one of {quoted}")


def _package_names(package: object) -> str:
    if isinstance(package, str):
        names = [package]
    elif isinstance(package, (list, tuple)):
        names = [item if isinstance(item, str) else str(item) for item in package]
    else:
        names = [str(package)]
    return "&pkgname=".join(names)


def _repo_url() -> str:
    root = environ.get("RSPM_ROOT", _DEFAULT_RSPM)
    repo_id = environ.get("RSPM_REPO_ID", _DEFAULT_REPO_ID)
    return f"{root}/__api__/repos/{repo_id}"


def _description_path(path: str) -> str:
    return ospath.abspath(ospath.join(ospath.expanduser(path), "DESCRIPTION"))


def _sh_quote(text: str) -> str:
    """R ``shQuote(text, type = "sh")``."""

    if "'" not in text:
        return "'" + text + "'"
    escaped = re.sub(r'(["$`\\])', r"\\\1", text)
    return '"' + escaped + '"'


def _curl_stdout(curl: str, args: list[str]) -> str:
    """Run curl the way ``system2(stdout = TRUE)`` does, through ``sh -c``."""

    command = " ".join([_sh_quote(curl), *args])
    completed = subprocess.run(
        ["/bin/sh", "-c", command],
        stdout=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(_CURL_FAILED)
    return completed.stdout.decode("utf-8")


def _parse_json(text: str) -> object:
    """Parse text the way remotes' ``json$parse`` does.

    Quotes are stripped and escape sequences are left as written.
    ``json.loads`` would turn ``\\n`` into a newline.
    """

    tokens = [
        match.group(0)
        for match in _TOKEN_RE.finditer(text)
        if not match.group(0).isspace()
    ]
    parser = _Parser(tokens)
    parser.read()
    return parser.parse_value()


class _Parser:
    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens
        self.ptr = 0
        self.token = "EOF"

    def read(self) -> None:
        if self.ptr < len(self.tokens):
            self.token = self.tokens[self.ptr]
            self.ptr += 1
        else:
            self.token = "EOF"

    def parse_value(self) -> object:
        if self.token == "{":
            return self.parse_object()
        if self.token == "[":
            return self.parse_array()
        if self.token == "EOF" or (
            len(self.token) == 1 and self.token not in "0123456789"
        ):
            raise RuntimeError(f"JSON: EXPECTED value GOT {self.token}")
        return _j2r(self.token)

    def parse_object(self) -> dict[str, object]:
        result: dict[str, object] = {}
        self.read()
        while self.token != "}":
            if _is_string_token(self.token):
                key = _j2r(self.token)
            else:
                raise RuntimeError(f"JSON: EXPECTED string GOT {self.token}")
            if not isinstance(key, str):
                raise RuntimeError(f"JSON: EXPECTED string GOT {self.token}")
            self.read()
            if self.token != ":":
                raise RuntimeError(f"JSON: EXPECTED : GOT {self.token}")
            self.read()
            result[key] = self.parse_value()
            self.read()
            if self.token == "}":
                break
            if self.token != ",":
                raise RuntimeError(f"JSON: EXPECTED , or }} GOT {self.token}")
            self.read()
        return result

    def parse_array(self) -> list[object]:
        result: list[object] = []
        self.read()
        while self.token != "]":
            result.append(self.parse_value())
            self.read()
            if self.token == "]":
                break
            if self.token != ",":
                raise RuntimeError(f"JSON: EXPECTED , GOT {self.token}")
            self.read()
        return result


def _is_string_token(token: str) -> bool:
    return len(token) >= 2 and token[0] == '"' and token[-1] == '"'


def _j2r(token: str) -> object:
    if token == "null":
        return None
    if token == "true":
        return True
    if token == "false":
        return False
    if _is_string_token(token):
        return token[1:-1]
    try:
        return float(token)
    except ValueError:
        return math.nan


def _commands(parsed: object, groups: str, nested: tuple[str, ...]) -> list[str]:
    if isinstance(parsed, dict):
        error = _dollar(parsed, "error")
        if error is not None:
            if isinstance(error, str):
                raise RuntimeError(error)
            raise RuntimeError(_number_text(error) if _is_atom(error) else str(error))
        pre_top = parsed.get("pre_install")
        install_top = parsed.get("install_scripts")
        group_value = parsed.get(groups)
    else:
        pre_top = None
        install_top = None
        group_value = None
    pre = _unique(_leaves([pre_top, *_pluck_each(group_value, nested + ("pre_install",))]))
    install = _unique(
        _leaves([install_top, *_pluck_each(group_value, nested + ("install_scripts",))])
    )
    return pre + install


def _dollar(obj: dict[str, object], name: str) -> object | None:
    """R's ``$``: an exact name wins, otherwise one unique prefix."""

    if name in obj:
        return obj[name]
    hits = [key for key in obj if key.startswith(name)]
    if len(hits) == 1:
        return obj[hits[0]]
    return None


def _pluck_each(groups: object, keys: tuple[str, ...]) -> list[object]:
    if groups is None:
        return []
    if isinstance(groups, dict):
        items = list(groups.values())
    elif isinstance(groups, list):
        items = groups
    else:
        items = [groups]
    return [_pluck(item, keys) for item in items]


def _pluck(obj: object, keys: tuple[str, ...]) -> object:
    current = obj
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current


def _leaves(value: object) -> list[str]:
    found: list[str] = []

    def walk(item: object) -> None:
        if item is None:
            return
        if isinstance(item, str):
            found.append(item)
            return
        if isinstance(item, bool):
            found.append("TRUE" if item else "FALSE")
            return
        if isinstance(item, (int, float)):
            found.append(_number_text(item))
            return
        if isinstance(item, list):
            for child in item:
                walk(child)
            return
        if isinstance(item, dict):
            for child in item.values():
                walk(child)

    walk(value)
    return found


def _is_atom(value: object) -> bool:
    return isinstance(value, (str, bool, int, float))


def _number_text(value: object) -> str:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    number = float(value)  # type: ignore[arg-type]
    if math.isnan(number):
        return "NaN"
    if number == math.inf:
        return "Inf"
    if number == -math.inf:
        return "-Inf"
    if number.is_integer():
        return str(int(number))
    return format(number, ".15g")


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
