import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rstudioapi.as_document_range import (
    as_document_range,
    document_range,
    print_document_range,
)

rng = document_range((1.0, 2.0, 3.0, 4.0))
print_document_range(as_document_range(rng))
print_document_range(as_document_range((5.0, 6.0, 7.0, 8.0)))
