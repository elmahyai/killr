import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.gmmhd_family import gmmhd

try:
    gmmhd({})
except Exception as exc:
    print(type(exc).__name__)
    print(str(exc))
