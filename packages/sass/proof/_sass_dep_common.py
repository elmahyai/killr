"""Shared canonical forms for the sass html-dependency proofs.

Mirrors _sass_dep_common.R. A dependency is compared by its identity, its
stylesheet text, and the md5 of each file in its directory when all_files is
set. A google_local dependency is rendered here, from the fixture cache, the
same way R renders it.
"""

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

PROOF = Path(__file__).resolve().parent
FIXTURES = PROOF / "fixtures"

# Make packages/ importable so `sass.<module>` resolves to packages/sass/<module>.py.
sys.path.insert(0, str(PROOF.parent.parent))

from sass._sass_values import HtmlDep  # noqa: E402
from sass.as_sass import SassHtmlVector  # noqa: E402
from sass.font_google import render_google_local  # noqa: E402


class ManifestCache:
    """The fixture cache, read from the same manifest.json that R reads.

    get_file(key, outfile) copies the file under key to outfile, as R's
    file cache does. Keys are the href and the font basenames.
    """

    def __init__(self, directory):
        directory = Path(directory)
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        self._files = {manifest["href"]: str(directory / manifest["css"])}
        for name, path in manifest["fonts"].items():
            self._files[name] = str(directory / path)

    def get_file(self, key, outfile, overwrite=True):
        src = self._files.get(key)
        if src is None:
            return False
        shutil.copyfile(src, outfile)
        return True

    def set_file(self, key, file):
        return False


def google_cache():
    return ManifestCache(FIXTURES / "google_local")


def proof_fixture(*parts):
    return str(FIXTURES.joinpath(*parts))


def _md5(path):
    with open(path, "rb") as fh:
        return hashlib.md5(fh.read()).hexdigest()


def canon_html(d: HtmlDep) -> dict:
    if d.kind == "google_local" and d.src is None:
        d = render_google_local(d)
    files = None
    if d.all_files and d.src is not None:
        files = [{"name": n, "md5": _md5(os.path.join(d.src, n))}
                 for n in sorted(os.listdir(d.src))]
    return {
        "name": d.name,
        "version": d.version,
        "kind": d.kind,
        "href": d.href,
        "head": d.head,
        "stylesheet": d.stylesheet,
        "files": files,
    }


def _deps(deps):
    if deps is None:
        return None
    if isinstance(deps, HtmlDep):
        deps = [deps]
    return [canon_html(d) for d in deps]


def canon_collection(fc) -> dict:
    return {
        "families": list(fc.families),
        "default_flag": fc.default_flag is True,
        "html_deps": [canon_html(d) for d in fc.html_deps],
    }


def as_html_case(x) -> dict:
    if isinstance(x, SassHtmlVector):
        text = list(x)
    else:
        text = str(x)
    return {
        "text": text,
        "html_dependencies": _deps(getattr(x, "html_dependencies", None)),
    }
