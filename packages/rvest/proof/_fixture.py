import sys
sys.path[:0] = ["packages/xml2", "packages/rvest"]
from rvest.rvest import *

HTML = minimal_html(
    "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>x</td></tr>"
    "<tr><td colspan='2'>2</td></tr></table><p>Hello <br> world</p>"
)
