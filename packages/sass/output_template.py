"""Translation of sass::output_template().

output_template() returns a function. That function builds the output path for
one compile. With a suffix, the directory is path/dirname+suffix, as R's
file.path() does. Without one, R's tempfile() picks a random name. The
directory is created either way.
"""

import os
import tempfile

_STYLE_CODES = {"nested": 0, "expanded": 1, "compact": 2, "compressed": 3}


def output_template(basename="sass", dirname=None, fileext=None, path=None):
    dirname = basename if dirname is None else dirname
    path = tempfile.gettempdir() if path is None else str(path)

    def template(options=None, suffix=None):
        options = options or {}
        style = options.get("output_style")
        style = _STYLE_CODES.get(style, style)
        ext = fileext if fileext is not None else (".min.css" if style in (2, 3) else ".css")
        if suffix is None:
            out_dir = tempfile.mkdtemp(prefix=dirname, dir=path)
        else:
            out_dir = f"{path}/{dirname}{suffix}"
        os.makedirs(out_dir, exist_ok=True)
        return f"{out_dir}/{basename}{ext}"

    return template
