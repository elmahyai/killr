"""Drop Sweave code chunks, leaving the documentation lines."""

import re
from pathlib import Path

_DOC = re.compile(r"^@")
_CODE = re.compile(r"^<<(.*)>>=.*")


def sweave_tex_filter(ifile, encoding="unknown"):
    """Blank code chunks in a noweb vignette. Documentation lines stay."""
    path = ifile["filename"] if isinstance(ifile, dict) and "filename" in ifile else ifile
    lines = Path(path).read_text(encoding="utf-8", errors="surrogateescape").splitlines()
    if encoding not in ("unknown", "UTF-8", "utf-8"):
        raw = "\n".join(lines).encode(encoding, errors="replace")
        lines = raw.decode("utf-8", errors="replace").splitlines()
    text = 1
    code = 0
    marks = [(index + 1, text) for index, line in enumerate(lines) if _DOC.search(line)]
    marks += [(index + 1, code) for index, line in enumerate(lines) if _CODE.search(line)]
    marks.sort()
    last = 0
    state = text
    for line_no, kind in marks:
        if state == code:
            for index in range(last, line_no):
                lines[index] = ""
        else:
            lines[line_no - 1] = ""
        state = kind
        last = line_no
    return lines
