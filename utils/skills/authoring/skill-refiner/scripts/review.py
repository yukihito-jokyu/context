#!/usr/bin/env python3
"""Render and serve an HTML review; only explicit submissions change the workflow."""
import argparse
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import sys
from urllib.parse import unquote, urlsplit

from refine import RefineError, atomic_json, contained, human_response, integrity, locked, read_json


TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "review.html"
STAGES = {
    "input_review": ("入力の確認", [("approve", "このスキルと題材で実行する")]),
    "generating": ("成果物を作成中", []),
    "feedback_review": ("成果物への指摘", [("feedback", "指摘を送信して評価基準の作成へ進む")]),
    "rubric_needed": ("評価基準を作成中", []),
    "rubric_review": ("評価基準の確認", [("approve", "この版の評価基準を承認する")]),
    "evaluating": ("新しい担当が評価中", []),
    "analysis_needed": ("評価結果と改善案を分析中", []),
    "analysis_review": ("改善案の確認", [("approve", "この版の改善案を承認する")]),
    "editing": ("承認した改善案を候補版へ反映済み", []),
    "results_review": ("再評価の結果と次の進め方", [("step", "各回の改善案を確認して進める"),
                         ("loop", "確認した範囲で最大3回の自動ループへ進む")]),
    "final_review": ("合格した候補版の最終確認", [("approve", "この候補版の正本反映を承認する")]),
    "promotion_ready": ("正本反映の承認済み", []),
    "complete": ("正本へ反映済み", []),
    "error_review": ("実行失敗・品質の評価は未完了", [("retry", "失敗した題材を新規担当で再実行する")]),
    "paused": ("一時停止中", [("resume", "確認を再開する")]),
}


def render(state, token=""):
    state = dict(state)
    title, actions = STAGES[state["stage"]]
    state["stage_title"] = title
    state["actions"] = actions + [("comment", "指摘を送信する")]
    if state["stage"] not in ("complete", "paused"):
        state["actions"].append(("pause", "停止して確認する"))
    state["rubric_data"] = read_json(state["rubric"]["path"]) if state["rubric"] else None
    state["analysis_data"] = read_json(state["analysis"]["path"]) if state["analysis"] else None
    # Do not expose the server token, parent history or control files to artifact frames.
    state["artifacts"] = []
    for run in state["runs"]:
        if run["role"] == "generate" and run["status"] == "complete":
            for file in sorted(Path(run["output"]).rglob("*")):
                if file.is_file() and not file.is_symlink():
                    rel = str(file.relative_to(state["workspace"]))
                    state["artifacts"].append({"case": run["case"], "iteration": run["iteration"],
                                               "path": rel, "html": file.suffix.lower() == ".html"})
    data = json.dumps({"state": state, "token": token}, ensure_ascii=False).replace("<", "\\u003c")
    return TEMPLATE.read_text(encoding="utf-8").replace("__REVIEW_DATA__", data)


def make_server(workspace, port=0):
    workspace = Path(workspace).resolve()
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, code, value, content_type="application/json; charset=utf-8", artifact=False):
            raw = value if isinstance(value, bytes) else value.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; "
                             "script-src 'unsafe-inline'; img-src 'self' data:; " +
                             ("connect-src 'none'; frame-src 'none'" if artifact else
                              "connect-src 'self'; frame-src 'self'; form-action 'self'"))
            self.end_headers()
            self.wfile.write(raw)

        def check_host(self):
            require_host = f"127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host") != require_host:
                raise RefineError("unrecognized Host")

        def do_GET(self):
            try:
                self.check_host()
                route = urlsplit(self.path).path
                state = read_json(workspace / "state.json")
                integrity(state)
                if route in ("/", "/review.html"):
                    self.send(200, render(state, token), "text/html; charset=utf-8")
                elif route.startswith("/artifact/"):
                    file = contained(workspace, workspace / unquote(route[len("/artifact/"):]))
                    allowed = [Path(r["output"]).resolve() for r in state["runs"]
                               if r["status"] == "complete" and r["role"] == "generate"]
                    if not any(file.is_relative_to(root) for root in allowed) or not file.is_file():
                        raise RefineError("artifact is unavailable")
                    is_html = file.suffix.lower() == ".html"
                    self.send(200, file.read_bytes(), "text/html; charset=utf-8" if is_html else
                              "text/plain; charset=utf-8", artifact=True)
                else:
                    self.send(404, json.dumps({"error": "not found"}))
            except (RefineError, OSError, ValueError) as exc:
                self.send(409, json.dumps({"error": str(exc)}))

        def do_POST(self):
            try:
                self.check_host()
                if urlsplit(self.path).path != "/api/respond":
                    self.send(404, json.dumps({"error": "not found"}))
                    return
                expected_origin = f"http://127.0.0.1:{self.server.server_port}"
                if self.headers.get("Origin") != expected_origin or not secrets.compare_digest(
                        self.headers.get("X-Review-Token", ""), token):
                    raise RefineError("submit from this review page")
                size = int(self.headers.get("Content-Length", 0))
                if not 0 < size <= 262144:
                    raise RefineError("invalid response size")
                response = json.loads(self.rfile.read(size))
                with locked(workspace) as state:
                    record = human_response(state, response)
                self.send(200, json.dumps({"saved": record["id"]}))
            except (RefineError, OSError, ValueError, TypeError) as exc:
                self.send(409, json.dumps({"error": str(exc)}, ensure_ascii=False))

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--static", action="store_true")
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    state = read_json(workspace / "state.json")
    integrity(state)
    (workspace / "review.html").write_text(render(state), encoding="utf-8")
    if args.static:
        print(workspace / "review.html")
        return
    server = make_server(workspace, args.port)
    info = {"url": f"http://127.0.0.1:{server.server_port}/review.html", "port": server.server_port}
    atomic_json(workspace / "review-server.json", info)
    print(info["url"], flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    try:
        main()
    except (RefineError, OSError, ValueError) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        sys.exit(2)
