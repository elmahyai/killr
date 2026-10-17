from curl import curl_download
from pathlib import Path
import tempfile
path = Path(tempfile.mktemp())
path.write_bytes(b'abc')
