import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rstudioapi.as_document_position import (
    as_document_position,
    document_position,
    print_document_position,
)

pos = document_position(1, 5)
print_document_position(as_document_position(pos))
print_document_position(as_document_position((3.0, 7.0)))
