import ctypes
import json
import socket
import statistics
import sys
import threading
import time
import warnings

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools/gtools")
from set_tcp_no_delay import Socket, setTCPNoDelay

server = socket.socket()
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(("127.0.0.1", 0))
server.listen(1)
port = server.getsockname()[1]


def _accept():
    conn, _addr = server.accept()
    time.sleep(20)
    conn.close()


threading.Thread(target=_accept, daemon=True).start()
client = socket.create_connection(("127.0.0.1", port))
ctypes.set_errno(0)


def flag():
    return client.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY)


def one():
    bits = [
        f"{setTCPNoDelay(client, True)}|{flag()}",
        f"{setTCPNoDelay(client, False)}|{flag()}",
        f"{setTCPNoDelay(client)}|{flag()}",
        f"{setTCPNoDelay(client, 2)}|{flag()}",
        f"{setTCPNoDelay(client, 0)}|{flag()}",
        f"{setTCPNoDelay(client, -1)}|{flag()}",
        f"{setTCPNoDelay(client, 0.9)}|{flag()}",
        f"{setTCPNoDelay(client, 1.9)}|{flag()}",
        f"{setTCPNoDelay(client, [False, True])}|{flag()}",
    ]
    return "|".join(bits)


one()
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out_dir = "/home/ahmed/killr_projects/killr/packages/gtools/docs/output"
shown = setTCPNoDelay(client, True)
with open(f"{out_dir}/setTCPNoDelay-python.txt", "w", encoding="utf-8") as handle:
    handle.write(shown + "\n")


def err(func):
    try:
        func()
    except RuntimeError as exc:
        return str(exc)
    raise RuntimeError("expected an error")


stale_bad = err(lambda: setTCPNoDelay(Socket(99999), True))
after_bad = f"{setTCPNoDelay(client, False)}|{flag()}"
stale_fd0 = err(lambda: setTCPNoDelay(Socket(0), True))
after_fd0 = f"{setTCPNoDelay(client, True)}|{flag()}"
plain = err(lambda: setTCPNoDelay(1, True))
plain_list = err(lambda: setTCPNoDelay([1], True))
na_msg = err(lambda: setTCPNoDelay(client, None))

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    try:
        setTCPNoDelay(client, "yes")
        char_msg = "SUCCESS"
    except RuntimeError as exc:
        char_msg = str(exc)
char_out = "|".join(
    [f"WARN:{item.message}" for item in caught] + [f"ERR:{char_msg}"]
)

value = "|".join(
    [
        value,
        stale_bad,
        after_bad,
        stale_fd0,
        after_fd0,
        plain,
        plain_list,
        na_msg,
        char_out,
    ]
)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
client.close()
server.close()
