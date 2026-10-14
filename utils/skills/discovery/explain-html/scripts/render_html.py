#!/usr/bin/env python3
"""Assemble an authored page model into a self-contained explanation HTML.

body_html/overview_html are trusted author-produced markup; not a user-upload API.
This assembly step does not prove factual correctness or source completeness.
"""
import argparse
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def render(model):
    pages = model['pages']
    if not pages:
        raise ValueError('At least one page is required')
    ids = [p['id'] for p in pages]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r'[a-z][a-z0-9-]*', i) for i in ids):
        raise ValueError('Page IDs must be unique lowercase kebab-case')
    groups = list(dict.fromkeys(p.get('group', 'start') for p in pages))
    escape = html.escape
    concern = '<nav class="concern-nav" aria-label="関心">'
    topic = ''
    for group in groups:
        members = [p for p in pages if p.get('group', 'start') == group]
        label = model.get('groups', {}).get(group, group)
        concern += f'<a data-group="{escape(group)}" href="#{members[0]["id"]}">{escape(label)}</a>'
        topic += f'<nav class="topic-nav" data-topic-group="{escape(group)}" aria-label="ページ">'
        topic += ''.join(f'<a href="#{p["id"]}">{escape(p["label"])}</a>' for p in members) + '</nav>'
    concern += '</nav>'
    markup = ''
    for p in pages:
        pid, label = p['id'], escape(p['label'])
        mode = p.get('overview_mode', 'diagram')
        if mode not in ('diagram', 'text'):
            raise ValueError('Unknown overview mode')
        reason = p.get('overview_reason', '').strip()
        if mode == 'text' and not reason:
            raise ValueError('Text overview requires an explicit reason')
        attributes = f' data-overview-mode="text" data-overview-reason="{escape(reason, quote=True)}"' if mode == 'text' else ''
        markup += f'<section id="{pid}" class="concern-page" data-page{attributes} data-group="{escape(p.get("group", "start"))}" data-label="{label}" tabindex="-1" aria-labelledby="{pid}-title"><h2 id="{pid}-title">{label}</h2>'
        markup += p.get('intro_html', '') + p['overview_html'] + p['body_html'] + '</section>'
    values = {'TITLE':escape(model['title']), 'SCOPE':escape(model['scope']),
              'CONCERN_NAV_HTML':concern, 'TOPIC_NAV_HTML':topic, 'PAGES_HTML':markup,
              'NAVIGATION_SCRIPT':(ROOT/'assets/navigation.js').read_text(),
              'FLOW_SCRIPT':(ROOT/'assets/flow.js').read_text()}
    source = (ROOT/'assets/explanation.html').read_text()
    source = re.sub(r'\{\{([A-Z_]+)\}\}', lambda m: values[m[1]], source)
    if re.search(r'\{\{[A-Z_]+\}\}', source):
        raise ValueError('Unresolved authored placeholder')
    return source

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--baseline',type=Path,help='Prior article: reject code loss and broken local references before writing')
    args = parser.parse_args()
    from check_archify import check as check_archify
    from check_diagram_delegation import check as check_delegation
    root=args.manifest.resolve().parent
    if not args.output.resolve().is_relative_to(root):raise SystemExit('Output must be inside manifest root')
    manifest=json.loads(args.manifest.read_text())
    candidate=render(json.loads(args.model.read_text()))
    if args.baseline:
        from check_article_content import check as check_content
        retention=check_content(args.baseline.read_text(),candidate)
        if not retention['pass']:
            print(json.dumps({'content_retention':retention},ensure_ascii=False,indent=2))
            raise SystemExit(1)
    declarations=check_delegation(manifest,root)
    provenance=check_archify(manifest,root,candidate)
    if not declarations['pass'] or not provenance['pass']:
        print(json.dumps({'delegation':declarations,'archify':provenance},ensure_ascii=False,indent=2))
        raise SystemExit(1)
    args.output.write_text(candidate, encoding='utf-8')
