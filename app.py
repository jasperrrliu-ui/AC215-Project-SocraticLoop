"""Zero-dependency local API and web server for the SocraticLoop MVP."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from socratic_loop.workflow import DemoSession, run_demo

ROOT = Path(__file__).parent
SESSIONS = {}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - stdlib handler API
        path = urlparse(self.path).path
        if path == "/api/demo":
            self._send(run_demo())
        elif path in {"/", "/index.html"}:
            self._send_file(ROOT / "frontend" / "index.html", "text/html; charset=utf-8")
        elif path.startswith("/api/sessions/"):
            session_id = path.rsplit("/", 1)[-1]
            session = SESSIONS.get(session_id)
            if session is None:
                self.send_error(404, "Unknown session")
            else:
                self._send(session.snapshot())
        else:
            self.send_error(404)

    def do_POST(self):  # noqa: N802 - stdlib handler API
        path = urlparse(self.path).path
        payload = self._read_json()
        if path == "/api/sessions":
            session = DemoSession(payload.get("question"))
            SESSIONS[session.id] = session
            self._send(session.start(), status=201)
            return
        if path.startswith("/api/sessions/") and path.endswith("/checkpoints"):
            session_id = path.split("/")[3]
            session = SESSIONS.get(session_id)
            if session is None:
                self.send_error(404, "Unknown session")
                return
            try:
                self._send(session.answer(payload["checkpoint_id"], payload["answer"]))
            except (KeyError, TypeError) as error:
                self.send_error(400, str(error))
            return
        self.send_error(404)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _send(self, payload, status=200):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, content_type):
        if not path.exists():
            self.send_error(404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print("SocraticLoop MVP: http://127.0.0.1:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
