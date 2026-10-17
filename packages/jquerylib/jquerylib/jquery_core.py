"""The jQuery dependency bundled by jquerylib."""


def jquery_core() -> dict:
    """Return the htmlDependency description for jQuery 3.6.0."""
    return {
        "name": "jquery",
        "version": "3.6.0",
        "src": {"file": "lib/3.6.0"},
        "meta": None,
        "script": "jquery-3.6.0.min.js",
        "stylesheet": None,
        "head": None,
        "attachment": None,
        "package": "jquerylib",
        "all_files": True,
    }
