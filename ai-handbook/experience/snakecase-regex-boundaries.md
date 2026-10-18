`snakecase` applies its parsing regexes sequentially, so uppercase runs, digit
runs, and non-alphanumeric separators must be handled in the documented order.
Camel-case splitting preserves underscores between adjacent digits; ordinary
Python `str.split("_")` loses that distinction.
