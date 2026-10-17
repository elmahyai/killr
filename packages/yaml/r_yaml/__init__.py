"""Python translation of the R package yaml.

The import name is r_yaml. PyYAML already owns yaml, and it parses the
YAML 1.1 events. yes/no, merges, and as.yaml's layout are this package.
"""

from r_yaml.emit import as_yaml
from r_yaml.load import yaml_load
from r_yaml.read_yaml import read_yaml
from r_yaml.verbatim_logical import verbatim_logical
from r_yaml.write_yaml import write_yaml
from r_yaml.yaml_load_file import yaml_load_file

__all__ = [
    "as_yaml",
    "read_yaml",
    "verbatim_logical",
    "write_yaml",
    "yaml_load",
    "yaml_load_file",
]
