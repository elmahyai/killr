"""Python translation of the R package glue.

Braces are Python expressions. ``glue_safe`` only looks up a name.
``glue_sql`` quotes the way RSQLite does and does not send a query.
``glue_col`` applies the ANSI codes crayon uses for the named styles.
"""

from glue.color import glue_col, glue_data_col
from glue.interpolate import as_glue, glue, glue_collapse, glue_data
from glue.quoting import backtick, double_quote, single_quote
from glue.safe import glue_data_safe, glue_safe
from glue.sql import Id, SQL, glue_data_sql, glue_sql, glue_sql_collapse, sqlite
from glue.trim import trim
from glue._eval import identity_transformer
from glue._text import NA

__all__ = [
    "Id",
    "NA",
    "SQL",
    "as_glue",
    "backtick",
    "double_quote",
    "glue",
    "glue_col",
    "glue_collapse",
    "glue_data",
    "glue_data_col",
    "glue_data_safe",
    "glue_data_sql",
    "glue_safe",
    "glue_sql",
    "glue_sql_collapse",
    "identity_transformer",
    "single_quote",
    "sqlite",
    "trim",
]
