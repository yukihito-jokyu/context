#!/usr/bin/env python3
"""Serve a report, open it, and wait until validated feedback JSON is submitted."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import threading
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


MAX_FEEDBACK_BYTES = 2 * 1024 * 1024


def validate_feedback(value: object) -> dict:
    if not isinstance(value, dict) or value.get("schema_version") != "1.0":
        raise ValueError("schema_version=1.0 のobjectが必要です")
    if not isinstance(value.get("report"), dict):
        raise ValueError("reportが必要です")
    if not isinstance(value.get("reviews"), list) or not isinstance(value.get("manual_comments"), list):
        raise ValueError("reviewsとmanual_commentsは配列である必要があります")
    for item in value["reviews"]:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("review_id"), str)
            or not isinstance(item.get("approved"), bool)
            or not isinstance(item.get("feedback"), str)
        ):
            raise ValueError("各reviewにはreview_id、approved真偽値、feedback文字列が必要です")
    for item in value["manual_comments"]:
        required = {"comment_id", "file", "side", "lines", "line_range", "feedback"}
        if not isinstance(item, dict) or not required.issubset(item) or not isinstance(item["lines"], list):
            raise ValueError("manual_commentの形式が不正です")
    return value


def make_handler(directory: Path, feedback_path: Path, submitted: threading.Event):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, format: str, *args) -> None:
            return

        def do_POST(self) -> None:
            if self.path != "/submit":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_FEEDBACK_BYTES:
                    raise ValueError("送信サイズが不正です")
                value = validate_feedback(json.loads(self.rfile.read(length).decode("utf-8")))
                if feedback_path.exists():
                    raise FileExistsError(f"既に存在します: {feedback_path}")
                temporary = feedback_path.with_suffix(feedback_path.suffix + ".tmp")
                temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
                os.replace(temporary, feedback_path)
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(b'{"ok":true}')
                submitted.set()
            except Exception as error:
                payload = json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False).encode("utf-8")
                self.send_response(HTTPStatus.BAD_REQUEST)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--feedback", required=True, type=Path)
    parser.add_argument("--port-start", type=int, default=8765)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    report = args.report.resolve()
    feedback = args.feedback.resolve()
    if not report.is_file():
        raise FileNotFoundError(report)
    if feedback.exists():
        raise FileExistsError(feedback)
    if feedback.parent != report.parent:
        raise ValueError("feedbackはreportと同じディレクトリへ保存してください")

    submitted = threading.Event()
    handler = make_handler(report.parent, feedback, submitted)
    server = None
    for port in range(args.port_start, args.port_start + 11):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), handler)
            break
        except OSError:
            continue
    if server is None:
        raise OSError("利用可能なローカルポートがありません")
    server.timeout = 0.5

    url = f"http://127.0.0.1:{server.server_port}/{report.name}"
    print(f"READY {url}", flush=True)
    if not args.no_open:
        subprocess.run(["open", url], check=True)
    try:
        while not submitted.is_set():
            server.handle_request()
    finally:
        server.server_close()
    print(f"SUBMITTED {feedback}", flush=True)


if __name__ == "__main__":
    main()
