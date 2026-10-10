"""Validate review payloads from the receiver and downloaded JSON."""

def validate_payload(payload: object, metadata: dict, expected_id: str) -> dict:
    if not isinstance(payload, dict) or payload.get('snapshot_id') != expected_id:
        raise ValueError('snapshot mismatch')
    if payload.get('schema_version') != 1 or not isinstance(payload.get('submitted_at'), str):
        raise ValueError('invalid feedback schema or timestamp')
    items = payload.get('items')
    expected = {point['number']: point for point in metadata['review_points']}
    if not isinstance(items, list) or len(items) < len(expected):
        raise ValueError('review items mismatch')
    seen = set()
    for item in items:
        if not isinstance(item, dict) or type(item.get('number')) is not int or item['number'] < 1:
            raise ValueError('invalid review item')
        number = item['number']
        if number in seen:
            raise ValueError('duplicate review item')
        seen.add(number)
        if type(item.get('approved')) is not bool or not isinstance(item.get('comment'), str):
            raise ValueError('invalid review item response')
        for name in ('previously_approved', 'reopened'):
            if type(item.get(name)) is not bool:
                raise ValueError(f'invalid {name}')
        if number in expected:
            point = expected[number]
            if item.get('kind') != 'review_point' or item.get('status_at_render') != point.get('status', 'pending') or item.get('title') != point.get('title'):
                raise ValueError('review point mismatch')
            if item.get('previously_approved') != bool(point.get('approval_history')) or item.get('target') is not None or item.get('position') is not None:
                raise ValueError('review point history or target mismatch')
        else:
            if item.get('kind') != 'dom_annotation' or item.get('status_at_render') != 'pending' or item.get('previously_approved') or item.get('reopened'):
                raise ValueError('invalid DOM annotation')
            target, position = item.get('target'), item.get('position')
            if not isinstance(target, dict) or not all(isinstance(target.get(name), str) for name in ('selector', 'tag', 'text')) or not target.get('selector') or not target.get('tag') or not isinstance(target.get('target_key'), (str, type(None))):
                raise ValueError('invalid annotation target')
            if not isinstance(position, dict) or any(type(position.get(name)) not in (int, float) or not 0 <= position[name] <= 100 for name in ('x_percent', 'y_percent', 'width_percent', 'height_percent')):
                raise ValueError('invalid annotation position')
            if position['x_percent'] + position['width_percent'] > 100.01 or position['y_percent'] + position['height_percent'] > 100.01:
                raise ValueError('annotation position exceeds canvas')
    if not set(expected).issubset(seen):
        raise ValueError('missing review points')
    if [item['number'] for item in items] != sorted(item['number'] for item in items):
        raise ValueError('review items must be ordered by number')
    details = payload.get('screen_detail_feedback')
    valid_details = {detail['key'] for detail in metadata.get('screen_details', [])}
    if not isinstance(details, list) or any(not isinstance(detail, dict) or detail.get('detail_key') not in valid_details or not isinstance(detail.get('comment'), str) for detail in details):
        raise ValueError('invalid screen detail feedback')
    if len({detail['detail_key'] for detail in details}) != len(details):
        raise ValueError('duplicate screen detail feedback')
    if type(payload.get('screen_details_approved')) is not bool:
        raise ValueError('invalid screen details approval')
    if not isinstance(payload.get('general_comment'), str):
        raise ValueError('invalid general comment')
    return payload
