"""Roman numeral dictionary (``utils:::.romans`` in R 4.5.0)."""

from __future__ import annotations

# Named integer vector in R: c(M = 1000L, CM = 900L, ...).
romans: dict[str, int] = {
    "M": 1000,
    "CM": 900,
    "D": 500,
    "CD": 400,
    "C": 100,
    "XC": 90,
    "L": 50,
    "XL": 40,
    "X": 10,
    "IX": 9,
    "V": 5,
    "IV": 4,
    "I": 1,
}
