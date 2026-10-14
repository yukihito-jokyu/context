#!/usr/bin/env python3
"""Compare retained code and local references in two authored HTML files.

This checks text/IDs, not code execution, diagram semantics or comprehension.
"""
import argparse
from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote

VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
        'meta', 'param', 'source', 'track', 'wbr'}


class Content(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.ids = []
        self.anchors = []
        self.blocks = []
        self.lines = {}

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if attrs.get('id'):
            self.ids.append(attrs['id'])
        href = attrs.get('href', '')
        if tag == 'a' and href.startswith('#') and href != '#':
            self.anchors.append(unquote(href[1:]))
        if tag not in VOID:
            self.stack.append({'tag': tag, 'pre': tag == 'pre', 'text': [],
                               'line': attrs.get('id') if 'code-line' in
                               attrs.get('class', '').split() else None})

    def handle_endtag(self, tag):
        index = next((i for i in range(len(self.stack)-1, -1, -1)
                      if self.stack[i]['tag'] == tag), None)
        if index is None:
            return
        for frame in self.stack[index:]:
            if frame['pre']:
                self.blocks.append(''.join(frame['text']))
            if frame['line']:
                self.lines[frame['line']] = ''.join(frame['text'])
        del self.stack[index:]

    def handle_data(self, data):
        for frame in self.stack:
            if frame['pre'] or frame['line']:
                frame['text'].append(data)


def check(before, after):
    original, current = Content(), Content()
    original.feed(before)
    current.feed(after)
    missing = [text for text in original.blocks if text not in current.blocks]
    changed = [id for id, text in original.lines.items()
               if current.lines.get(id) != text]
    duplicates = sorted(id for id, count in Counter(current.ids).items() if count > 1)
    anchors = sorted(set(current.anchors) - set(current.ids))
    return {'pass': not (missing or changed or duplicates or anchors),
            'baseline_code_blocks': len(original.blocks),
            'current_code_blocks': len(current.blocks),
            'missing_code_blocks': missing,
            'baseline_code_lines': len(original.lines),
            'current_code_lines': len(current.lines),
            'changed_or_missing_code_lines': changed,
            'duplicate_ids': duplicates, 'missing_anchors': anchors,
            'scope': 'Exact decoded pre text and original code-line IDs/text, '
                     'duplicate IDs and local fragment targets. Repeated identical '
                     'blocks may share one retained copy. No runtime, factual '
                     'diagram, prose-quality or comprehension guarantee.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = check(args.before.read_text(), args.after.read_text())
    output = json.dumps(result, ensure_ascii=False, indent=2)+'\n'
    if args.report:
        args.report.write_text(output)
    print(output, end='')
    raise SystemExit(0 if result['pass'] else 1)
