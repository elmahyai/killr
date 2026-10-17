"""read_yaml: a file, a text string, or an open text stream."""

from r_yaml.load import yaml_load


def read_yaml(file=None, file_encoding="UTF-8", text=None, error_label=None, read_lines_warn=True, **options):
    """Read YAML from a path, a stream, or the text argument."""
    if file is None and text is not None:
        if error_label is None:
            error_label = None
        return yaml_load(text, error_label=error_label, **options)
    if isinstance(file, str):
        if error_label is None:
            error_label = file
        encoding = file_encoding or None
        with open(file, encoding=encoding) as handle:
            string = "\n".join(handle.read().splitlines())
        return yaml_load(string, error_label=error_label, **options)
    if hasattr(file, "read"):
        if error_label is None:
            error_label = getattr(file, "name", None)
        string = "\n".join(file.read().splitlines())
        return yaml_load(string, error_label=error_label, **options)
    raise ValueError("'file' must be a character string or connection")
