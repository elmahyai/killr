from curl import new_handle, curl_fetch_memory, handle_data
from pathlib import Path
import tempfile
path = Path(tempfile.mktemp())
path.write_bytes(b'abc')
def run():
    h = new_handle()
    curl_fetch_memory('file://' + str(path), h)
    return handle_data(h)['status_code']
