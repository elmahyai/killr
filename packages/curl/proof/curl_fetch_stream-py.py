from curl import curl_fetch_stream
from pathlib import Path
import tempfile
path = Path(tempfile.mktemp())
path.write_bytes(b'abc')
box = []
