import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rstudioapi.is_available import isAvailable

value = isAvailable()
if value is True:
    text = "TRUE"
elif value is False:
    text = "FALSE"
else:
    text = repr(value)
print("[1] " + text)
