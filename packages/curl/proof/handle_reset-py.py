from curl import new_handle, curl_fetch_memory, handle_reset, handle_data
from pathlib import Path
import tempfile
path = Path(tempfile.mktemp())
path.write_bytes(b'abc')
def run():
    h = new_handle()
    curl_fetch_memory('file://' + str(path), h)
    handle_reset(h)
    return not handle_data(h).get('url')
