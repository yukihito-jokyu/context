#!/usr/bin/env python3
"""Receive one feedback submission while one Vite server serves all snapshots."""
import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from common import load, snapshot_id
from feedback import validate_payload



parser = argparse.ArgumentParser()
parser.add_argument('--workspace', required=True, type=Path)
parser.add_argument('--snapshot', required=True)
parser.add_argument('--port', type=int, default=8765)
parser.add_argument('--review-url', default='http://127.0.0.1:5173/')
args = parser.parse_args()
root = args.workspace.resolve()
meta = load(root / 'discussion' / f'{args.snapshot}.json')
if snapshot_id(meta) != args.snapshot:
    raise SystemExit('snapshot mismatch')
output = root / 'discussion' / f'{args.snapshot}-feedback.json'
if output.exists():
    raise SystemExit(f'feedback already exists: {output}')
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def reply(self, status, body):
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def do_POST(self):
        if self.path != '/api/feedback':
            return self.reply(404, {'error': 'not found'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 1048576: raise ValueError('invalid body length')
            payload = validate_payload(json.loads(self.rfile.read(length)), meta, args.snapshot)
            with output.open('x', encoding='utf-8') as file:
                json.dump(payload, file, ensure_ascii=False, indent=2)
                file.write('\n')
        except FileExistsError: return self.reply(409, {'error': 'feedback already saved'})
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error: return self.reply(400, {'error': str(error)})
        self.reply(201, {'ok': True})
        print(f'FEEDBACK_RECEIVED={output}', flush=True)
        threading.Thread(target=self.server.shutdown, daemon=True).start()
server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
print(f'REVIEW_URL={args.review_url}', flush=True)
print(f'FEEDBACK_RECEIVER=http://127.0.0.1:{args.port}/api/feedback', flush=True)
server.serve_forever()
server.server_close()
