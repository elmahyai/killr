"""Translation of sass::sass_file."""

from pathlib import Path
from .sass_import import sass_import


def sass_file(input):
    path = Path(input).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Could not find file: '{input}'")
    # R returns a character import expression with sass_file metadata.
    result = sass_import(str(path))
    return result
