"""Python translations of the mime package."""
from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Mapping
from urllib.parse import unquote_plus

from .map_data import MIMEMAP, MIMEEXTRA


def mimemap() -> dict[str, str]:
    """Return the filename-extension to MIME-type table."""
    return dict(MIMEMAP)


def _file_ext(path: str) -> str:
    base = os.path.basename(path)
    # tools::file_ext treats a leading dot as having no extension.
    if base.startswith(".") and base.count(".") == 1:
        return ""
    return base.rsplit(".", 1)[1] if "." in base else ""


def guess_type(file, unknown="application/octet-stream", empty="text/plain",
               mime_extra=MIMEEXTRA, subtype=""):
    """Guess MIME types from filenames or extensions."""
    files = [file] if isinstance(file, str) else list(file)
    extra = {} if mime_extra is None else dict(mime_extra)
    exts = [_file_ext(str(x)) for x in files]
    result = [extra.get(ext.lower(), MIMEMAP.get(ext.lower(), unknown))
              if ext else empty for ext in exts]
    subs = [subtype] if isinstance(subtype, str) else list(subtype)
    if any(x != "" for x in subs):
        if len(result) != len(subs):
            raise ValueError("'subtype' must be of the same length as 'file'")
        result = [f"{typ}; {sub}" if sub else typ
                  for typ, sub in zip(result, subs)]
    return result[0] if isinstance(file, str) else result


def _read_input(inp, n=-1) -> bytes:
    value = inp.read(n) if n >= 0 else inp.read()
    if isinstance(value, str):
        return value.encode()
    return bytes(value or b"")


def _env_get(env, key):
    if isinstance(env, Mapping):
        return env.get(key)
    return getattr(env, key, None)


def parse_multipart(env):
    """Parse a Rook-style multipart request environment."""
    ctype = _env_get(env, "CONTENT_TYPE")
    if not ctype or not re.match(r"^multipart", str(ctype)):
        return None
    inp = _env_get(env, "rook.input")
    if inp is None and isinstance(env, Mapping):
        inp = env.get("rook.input") or env.get("rook_input")
    if inp is None:
        return None
    rewind = getattr(inp, "rewind", None)
    if rewind:
        rewind()
    body = _read_input(inp)
    m = re.search(r'boundary="?([^";,]+)', str(ctype), re.I)
    if not m:
        if rewind: rewind()
        return None
    boundary = m.group(1).encode()
    marker = b"--" + boundary
    length = _env_get(env, "CONTENT_LENGTH")
    if length is not None:
        try:
            if int(length) != len(body):
                # R uses the declared length while reading; reject malformed input.
                pass
        except (TypeError, ValueError):
            pass
    if not body.startswith(marker + b"\r\n"):
        if rewind: rewind()
        return None
    params = {}
    for rawpart in body[len(marker)+2:].split(marker):
        if rawpart.startswith(b"--"):
            break
        if rawpart.startswith(b"\r\n"):
            rawpart = rawpart[2:]
        if rawpart.endswith(b"\r\n"):
            rawpart = rawpart[:-2]
        if b"\r\n\r\n" not in rawpart:
            if rewind: rewind()
            return None
        rawhead, value = rawpart.split(b"\r\n\r\n", 1)
        head = rawhead.decode("latin1")
        disp = re.search(r"Content-Disposition:\s*[^\r\n]*", head, re.I)
        if not disp:
            if rewind: rewind()
            return None
        dline = disp.group(0)
        nm = re.search(r'\bname="?([^";\r\n]*)', dline, re.I)
        if not nm:
            if rewind: rewind()
            return None
        name = nm.group(1)
        fm = re.search(r'\bfilename="(.*?)"', dline, re.I)
        if not fm:
            fm = re.search(r"\bfilename=([^;\s]+)", dline, re.I)
        filename = fm.group(1) if fm else None
        tm = re.search(r"^Content-Type:\s*(.*)$", head, re.I | re.M)
        content_type = tm.group(1) if tm else None
        if filename is not None or content_type is not None:
            fd, path = tempfile.mkstemp()
            with os.fdopen(fd, "wb") as out:
                out.write(value)
            data = {"name": filename, "size": len(value),
                    "type": content_type, "datapath": path}
            params[name] = [data] if name not in params else params[name] + [data]
        else:
            if name.endswith("[]"):
                name = name[:-2]
                if name in params:
                    previous = params[name]
                    if isinstance(previous, list):
                        params[name] = previous + [value.rstrip(b"\r\n").decode()]
                    else:
                        params[name] = [previous, value.rstrip(b"\r\n").decode()]
                else:
                    params[name] = value.rstrip(b"\r\n").decode()
            else:
                params[name] = value.rstrip(b"\r\n").decode()
    if rewind: rewind()
    return params
