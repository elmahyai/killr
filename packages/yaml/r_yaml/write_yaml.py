"""write_yaml: as_yaml, then write the string."""

from r_yaml.emit import as_yaml


def write_yaml(x, file, file_encoding="UTF-8", **options):
    """Write the YAML form of x to a path or a stream."""
    result = as_yaml(x, **options)
    if isinstance(file, str):
        encoding = file_encoding or None
        with open(file, "w", encoding=encoding) as handle:
            handle.write(result)
        return result
    if hasattr(file, "write"):
        file.write(result)
        return result
    raise ValueError("'file' must be a character string or connection")
