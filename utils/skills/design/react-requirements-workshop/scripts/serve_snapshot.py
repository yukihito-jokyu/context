#!/usr/bin/env python3
"""Open an archived rendered snapshot from a later session."""
from __future__ import annotations
import argparse
import http.server
import tempfile
import zipfile
from pathlib import Path
from common import digest, load

parser = argparse.ArgumentParser()
parser.add_argument('--workspace', required=True, type=Path)
parser.add_argument('--snapshot', required=True)
parser.add_argument('--port', type=int, default=0)
args = parser.parse_args()
root = args.workspace.resolve()
record = load(root / 'discussion/rendered' / f'{args.snapshot}.json')
archive = root / 'discussion/rendered' / record['archive']
if record.get('snapshot_id') != args.snapshot or digest(archive) != record['sha256']['archive']:
    raise SystemExit('rendered snapshot changed')
with tempfile.TemporaryDirectory(prefix='react-snapshot-') as directory:
    destination = Path(directory).resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            resolved = (destination / member.filename).resolve()
            if not resolved.is_relative_to(destination):
                raise SystemExit('unsafe archive path')
        bundle.extractall(destination)
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=str(destination), **kw)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', args.port), handler)
    print(f'SNAPSHOT_URL=http://127.0.0.1:{server.server_port}/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
