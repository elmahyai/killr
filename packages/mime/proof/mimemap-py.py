import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
from mime.api import mimemap
m=mimemap(); print(f"length={len(m)} pdf={m.get('pdf')} html={m.get('html')} js={m.get('js')}")
