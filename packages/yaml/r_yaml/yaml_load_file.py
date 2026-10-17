"""yaml.load_file: read lines, then yaml_load."""

from r_yaml.load import yaml_load


def yaml_load_file(input, error_label=None, read_lines_warn=True, **options):
    """Load YAML from a path or a stream."""
    if isinstance(input, str):
        if error_label is None and input:
            error_label = input
        with open(input, encoding="UTF-8") as handle:
            lines = handle.read().splitlines()
    elif hasattr(input, "read"):
        if error_label is None:
            error_label = getattr(input, "name", None)
        lines = input.read().splitlines()
    else:
        raise ValueError("'input' must be a character string or connection")
    return yaml_load(lines, error_label=error_label, **options)
