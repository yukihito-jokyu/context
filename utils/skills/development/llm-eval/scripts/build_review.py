#!/usr/bin/env python3
"""Build offline review HTML. Usage: build_review.py --data review-data.json --output review.html"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def case_set(cases):
    if not isinstance(cases, list) or not cases:
        raise ValueError('cases must be a nonempty list')
    seen = set()
    for c in cases:
        if not isinstance(c, dict):
            raise ValueError('case must be an object')
        ident = c.get('id')
        if not isinstance(ident, str) or not re.fullmatch(r'[a-zA-Z0-9_-]+', ident) or ident == 'overall' or ident in seen:
            raise ValueError('invalid, reserved or duplicate case id')
        seen.add(ident)
        for field in ('label', 'basis', 'rule'):
            if not isinstance(c.get(field), str) or not c[field].strip():
                raise ValueError(f'{ident}: missing {field}')
        if 'input' not in c or 'expected' not in c:
            raise ValueError(f'{ident}: input and expected required')
    return seen


def validate(data):
    if not isinstance(data, dict):
        raise ValueError('data must be an object')
    for field in ('title', 'description', 'basis', 'plan'):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise ValueError(f'missing text: {field}')
    if not isinstance(data.get('limitations'), list) or not all(isinstance(v, str) for v in data['limitations']):
        raise ValueError('limitations must be a list of strings')
    if 'is_sample' in data and type(data['is_sample']) is not bool:
        raise ValueError('is_sample must be a boolean')
    case_set(data.get('cases'))
    if not isinstance(data.get('runs'), list):
        raise ValueError('runs must be a list, empty before evaluation')
    seen_runs = set()
    for run in data['runs']:
        if not isinstance(run, dict):
            raise ValueError('run must be an object')
        ident = run.get('id')
        if not isinstance(ident, str) or not re.fullmatch(r'[a-zA-Z0-9_-]+', ident) or ident in seen_runs:
            raise ValueError('invalid or duplicate run id')
        seen_runs.add(ident)
        if not isinstance(run.get('basis'), str) or not run['basis'].strip():
            raise ValueError(f'{ident}: basis required')
        if run.get('purpose') not in ('evaluation', 'exploratory'):
            raise ValueError(f'{ident}: purpose must be evaluation or exploratory')
        if run['purpose'] == 'evaluation' and not (isinstance(run.get('approval_ref'), str) and run['approval_ref'].strip()):
            raise ValueError(f'{ident}: evaluation requires prior approval reference')
        if 'cases' not in run:
            if run['basis'] != data['basis']:
                raise ValueError(f'{ident}: different basis requires historic cases snapshot')
            run['cases'] = data['cases']
        ids = case_set(run['cases'])
        if run['basis'] == data['basis'] and digest(run['cases']) != digest(data['cases']):
            raise ValueError(f'{ident}: same basis has different cases')
        run['comparison_key'] = digest(run['cases'])
        if not isinstance(run.get('details'), list):
            raise ValueError(f'{ident}: details required')
        scores = {}; seen = set(); excluded = 0
        for row in run['details']:
            if not isinstance(row, dict):
                raise ValueError(f'{ident}: detail must be an object')
            case = row.get('case_id'); rep = row.get('rep')
            if case not in ids or type(rep) is not int or rep < 0 or (case, rep) in seen:
                raise ValueError(f'{ident}: invalid or duplicate case/rep')
            seen.add((case, rep))
            if row.get('status') not in ('ok', 'refusal', 'truncated', 'error'):
                raise ValueError(f'{ident}: unsupported status')
            if 'actual' not in row:
                raise ValueError(f'{ident}: actual output or state required')
            score = row.get('score')
            if score is not None and not (isinstance(row.get('reason'), str) and row['reason'].strip()):
                raise ValueError(f'{ident}: scored detail requires reason')
            if score is not None and (type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1):
                raise ValueError(f'{ident}: scores must be normalized to 0..1 or null')
            if row['status'] in ('truncated', 'error') and score is not None:
                raise ValueError(f'{ident}: incomplete/error score must be null')
            if row['status'] in ('ok', 'refusal') and score is not None:
                scores.setdefault(case, []).append(score)
            else:
                excluded += 1
        errors = run.get('errors', 0)
        if type(errors) is not int or errors < 0:
            raise ValueError(f'{ident}: errors must be a nonnegative integer')
        run['case_scores'] = {k: sum(v)/len(v) for k, v in scores.items()}
        run['score'] = 100*sum(run['case_scores'].values())/len(scores) if scores else None
        run['scored'] = len(scores); run['planned'] = len(ids); run['excluded'] = excluded; run['errors'] = errors
    data.pop('fingerprint', None)
    data['fingerprint'] = digest(data)
    return data


def build(data):
    data = validate(data)
    template = (Path(__file__).resolve().parent.parent/'assets/review.html').read_text(encoding='utf-8')
    # Prevent input strings from closing the embedded script element.
    encoded = json.dumps(data, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    pattern = r'(<script type="application/json" id="review-data">).*?(</script>)'
    html, count = re.subn(pattern, lambda match: match[1] + encoded + match[2], template, count=1, flags=re.DOTALL)
    if count != 1:
        raise ValueError('template data block not found')
    return html


def main():
    parser = argparse.ArgumentParser(description='評価基準・結果・点数推移を確認する単体HTMLを作る')
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.data.read_text(encoding='utf-8'))
        html = build(data)
        if args.output.resolve() == args.data.resolve():
            raise ValueError('output must not overwrite input')
        if args.output.is_symlink():
            raise ValueError('refusing symlink output')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(html, encoding='utf-8')
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f'error: {exc}\n')
    print(args.output)


if __name__ == '__main__':
    main()
