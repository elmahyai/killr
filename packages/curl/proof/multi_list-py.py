from curl import new_pool, new_handle, multi_add, multi_list
from pathlib import Path
import tempfile
path = Path(tempfile.mktemp())
path.write_bytes(b'abc')
def run():
    pool = new_pool()
    multi_add(new_handle(url='file://' + str(path)), pool=pool)
    return len(multi_list(pool))
