"""Description of the bundled Font Awesome HTML dependency."""


def fa_html_dependency() -> dict:
    return {
        "name": "font-awesome",
        "version": "6.5.2",
        "src": {"file": "fontawesome"},
        "package": "fontawesome",
        "meta": None,
        "script": None,
        "stylesheet": ["css/all.min.css", "css/v4-shims.min.css"],
        "head": None,
        "attachment": None,
        "all_files": True,
    }
