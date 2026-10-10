#!/usr/bin/env python3
"""Serve the approved mock and save one feedback submission."""

from __future__ import annotations

import argparse
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


MAX_BODY_BYTES = 1024 * 1024


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--mock-dir", required=True, type=Path)
    parser.add_argument("--mock-file", default="002-feedback-workflow.html")
    parser.add_argument("--port", type=int, default=0)
    return parser.parse_args()


def validate_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    if not isinstance(payload.get("snapshot_id"), str) or not payload["snapshot_id"]:
        raise ValueError("snapshot_id is required")
    if not isinstance(payload.get("items"), list):
        raise ValueError("items must be an array")
    return payload


def main() -> None:
    args = parse_args()
    mock_dir = args.mock_dir.resolve(strict=True)
    run_dir = args.run_dir.resolve()
    output_path = run_dir / "feedback.json"
    run_dir.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise SystemExit(f"Refusing to overwrite: {output_path}")

    class ReviewHandler(SimpleHTTPRequestHandler):
        def __init__(self, *handler_args: Any, **handler_kwargs: Any) -> None:
            super().__init__(*handler_args, directory=str(mock_dir), **handler_kwargs)

        def log_message(self, format: str, *values: Any) -> None:
            return

        def send_json(self, status: int, body: dict[str, Any]) -> None:
            encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def do_POST(self) -> None:
            if self.path != "/api/feedback":
                self.send_json(404, {"ok": False, "error": "not found"})
                return
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
                if content_length <= 0 or content_length > MAX_BODY_BYTES:
                    raise ValueError("invalid content length")
                payload = validate_payload(json.loads(self.rfile.read(content_length)))
                with output_path.open("x", encoding="utf-8") as output_file:
                    json.dump(payload, output_file, ensure_ascii=False, indent=2)
                    output_file.write("\n")
            except (ValueError, json.JSONDecodeError) as error:
                self.send_json(400, {"ok": False, "error": str(error)})
                return
            except FileExistsError:
                self.send_json(409, {"ok": False, "error": "feedback already received"})
                return

            self.send_json(201, {"ok": True, "saved": "feedback.json"})
            print(f"FEEDBACK_RECEIVED={output_path}", flush=True)
            threading.Thread(target=self.server.shutdown, daemon=True).start()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), ReviewHandler)
    port = server.server_address[1]
    print(f"REVIEW_URL=http://127.0.0.1:{port}/{args.mock_file}", flush=True)
    print(f"OUTPUT_PATH={output_path}", flush=True)
    server.serve_forever()
    server.server_close()


if __name__ == "__main__":
    main()
