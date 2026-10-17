from _fixture import *
from http.server import HTTPServer, BaseHTTPRequestHandler
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"<p>ok</p>")
    def log_message(self, *a): pass
srv = HTTPServer(("127.0.0.1", 0), H)
import threading
threading.Thread(target=srv.serve_forever, daemon=True).start()
s = session(f"http://127.0.0.1:{srv.server_port}/")
print(is_session(s), s.response.status_code)
srv.shutdown()
