"""S3 shells for toRd and toHTML."""


def _class_label(obj):
    if obj is None:
        return '"NULL"'
    if isinstance(obj, bool):
        return '"logical"'
    if isinstance(obj, int):
        return '"c(\'integer\', \'numeric\')"'
    if isinstance(obj, float):
        return '"c(\'double\', \'numeric\')"'
    if isinstance(obj, str):
        return '"character"'
    return '"unknown"'


def to_html(obj, *args):
    """No toHTML method is registered for base objects."""
    label = _class_label(obj)
    raise ValueError(
        f"no applicable method for 'toHTML' applied to an object of class {label}"
    )


def to_rd(obj, *args):
    """Escape a value so it can sit in Rd text."""
    text = "" if obj is None else str(obj)
    text = text.replace("\\", "\\\\")
    text = text.replace("{", "\\{")
    text = text.replace("}", "\\}")
    text = text.replace("%", "\\%")
    return text
