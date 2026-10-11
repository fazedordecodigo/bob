"""API HTTP mínima para os testes da Action observarem o GitHub sem rede."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


class GitHubApi:
    """Estado mutável do servidor. Os testes leem o que a Action gravou."""

    def __init__(self) -> None:
        self.comments: list[dict[str, object]] = []
        self.artifacts: list[dict[str, object]] = []
        self.zips: dict[int, bytes] = {}
        self.require_auth = True
        self.write_status: int | None = None
        self.comment_pages: list[list[dict[str, object]]] | None = None
        self._next_id = 1
        self.redirect_downloads = False

    def add_comment(self, body: str, login: str = "github-actions[bot]") -> dict[str, object]:
        comment = {"id": self._next_id, "body": body, "user": {"login": login}}
        self._next_id += 1
        self.comments.append(comment)
        return comment


class _Server(ThreadingHTTPServer):
    def __init__(self, api: GitHubApi) -> None:
        self.api = api
        super().__init__(("127.0.0.1", 0), _Handler)


class _Handler(BaseHTTPRequestHandler):
    server: _Server

    def log_message(self, format: str, *args: object) -> None:
        return

    def _authorized(self) -> bool:
        if not self.server.api.require_auth:
            return True
        return self.headers.get("Authorization") == "Bearer test-token"

    def _read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        parsed = json.loads(raw.decode())
        if not isinstance(parsed, dict):
            raise ValueError("corpo JSON deve ser um objeto")
        return parsed

    def _send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/blob/"):
            artifact_id = int(parsed.path.rsplit("/", 1)[1])
            if self.headers.get("Authorization"):
                self._send_json({"message": "auth must not follow redirect"}, 400)
                return
            self._send_bytes(self.server.api.zips[artifact_id])
            return
        if not self._authorized():
            self._send_json({"message": "unauthorized"}, 401)
            return
        api = self.server.api
        if parsed.path.endswith("/comments"):
            page = int(parse_qs(parsed.query).get("page", ["1"])[0])
            pages = api.comment_pages
            if pages is None:
                self._send_json(api.comments)
                return
            index = page - 1
            payload = pages[index] if 0 <= index < len(pages) else []
            body = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            if index + 1 < len(pages):
                next_url = f"http://{self.headers['Host']}{parsed.path}?page={page + 1}"
                self.send_header("Link", f'<{next_url}>; rel="next"')
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path.endswith("/actions/artifacts"):
            name = parse_qs(parsed.query).get("name", [None])[0]
            artifacts = api.artifacts
            if name is not None:
                artifacts = [item for item in artifacts if item["name"] == name]
            self._send_json({"artifacts": artifacts})
            return
        marker = "/actions/artifacts/"
        if marker in parsed.path and parsed.path.endswith("/zip"):
            artifact_id = int(parsed.path.split(marker, 1)[1].split("/", 1)[0])
            payload = api.zips[artifact_id]
            if api.redirect_downloads:
                self.send_response(302)
                self.send_header("Location", f"http://{self.headers['Host']}/blob/{artifact_id}")
                self.end_headers()
                return
            self._send_bytes(payload)
            return
        self._send_json({"message": "not found"}, 404)

    def do_POST(self) -> None:
        if not self._authorized():
            self._send_json({"message": "unauthorized"}, 401)
            return
        if not self.path.split("?", 1)[0].endswith("/comments"):
            self._send_json({"message": "not found"}, 404)
            return
        payload = self._read_json()
        if self.server.api.write_status is not None:
            self._send_json({"message": "rejected"}, self.server.api.write_status)
            return
        comment = self.server.api.add_comment(str(payload["body"]))
        self._send_json(comment, 201)

    def do_PATCH(self) -> None:
        if not self._authorized():
            self._send_json({"message": "unauthorized"}, 401)
            return
        comment_path = self.path.split("?", 1)[0]
        comment_id = int(comment_path.rstrip("/").rsplit("/", 1)[1])
        payload = self._read_json()
        if self.server.api.write_status is not None:
            self._send_json({"message": "rejected"}, self.server.api.write_status)
            return
        for comment in self.server.api.comments:
            if comment["id"] == comment_id:
                comment["body"] = str(payload["body"])
                self._send_json(comment)
                return
        self._send_json({"message": "not found"}, 404)

    def _send_bytes(self, payload: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def serve(api: GitHubApi) -> tuple[_Server, str]:
    server = _Server(api)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    return server, f"http://{host}:{port}"
