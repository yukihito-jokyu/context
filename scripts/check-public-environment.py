"""Check tracked files, ZIP members and optionally main's history for local environment data."""
import argparse
import io
import pathlib
import re
import subprocess
import zipfile

RULES = {
    'user-home': re.compile(rb'/Users/[A-Za-z0-9._-]+(?=/|[\s"\x27<>\\]|$)'),
    'browser-version': re.compile(rb'Chrome/\d+(?:\.\d+){1,4}'),
    'local-architecture': re.compile(rb'arm64-darwin\d+|go version go[^\r\n"\\]*darwin/arm64'),
    'local-tool-output': re.compile(rb'(?:node: v\d|ruby: ruby \d|sqlite3: \d|clang: Apple clang version \d|swift: swift-driver version: \d|java: openjdk \d)'),
    'local-tool-inventory': re.compile(r'(?:tsc|lua|rustc|kotlinc|dotnet): (?:なし|あり)'.encode()),
    'local-xml-version': re.compile(rb'(?:xmllint: (?:xmllint: )?using libxml version|`xmllint`)\s+\d+'),
    'recorded-runtime-version': re.compile(rb'(?:Python|Node\.js|git version|git|ripgrep)\s+v?\d+\.\d+\.\d+(?![.\d]|\xe4\xbb\xa5\xe4\xb8\x8a)|Apple Git-\d+'),
}

def scan(data, location, failures, depth=0):
    if data.startswith(b'PK\x03\x04'):
        if depth >= 4:
            failures.append((location, 0, 'archive-depth'))
            return
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for item in archive.infolist():
                    if not item.is_dir():
                        scan(archive.read(item), location + '!' + item.filename, failures, depth + 1)
        except (OSError, zipfile.BadZipFile, RuntimeError):
            failures.append((location, 0, 'unreadable-archive'))
    elif b'\0' not in data[:8000]:
        for name, pattern in RULES.items():
            match = pattern.search(data)
            if match:
                failures.append((location, data.count(b'\n', 0, match.start()) + 1, name))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', action='store_true', help='scan every blob and commit reachable from main')
    args = parser.parse_args()
    root = pathlib.Path(__file__).resolve().parent.parent
    failures = []
    files = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    for relative in filter(None, files):
        file = root / relative
        if file.is_file():
            scan(file.read_bytes(), relative, failures)
    count = 0
    if args.history:
        objects = subprocess.check_output(['git', 'rev-list', '--objects', 'main'], cwd=root).splitlines()
        requests = b'\n'.join(line.split(b' ', 1)[0] for line in objects) + b'\n'
        stream = io.BytesIO(subprocess.check_output(['git', 'cat-file', '--batch'], input=requests, cwd=root))
        while True:
            header = stream.readline()
            if not header:
                break
            sha, kind, size = header.split()
            data = stream.read(int(size))
            stream.read(1)
            if kind in (b'blob', b'commit'):
                scan(data, 'git:' + sha.decode(), failures)
                count += 1
    for location, line, rule in failures:
        print(f'{location}:{line}: {rule} (value omitted)')
    print(f'Public environment check: {len(failures)} findings; {len(files) - 1} tracked files; {count} history objects')
    return bool(failures)

if __name__ == '__main__':
    raise SystemExit(main())
