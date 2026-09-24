# 画面案とフィードバックの形式

各案は `src/snapshots/NNN-slug.tsx` と `discussion/NNN-slug.json` の組にする。TSX は default export し、`main.tsx` は同じ案の TSX と JSON を import する。JSON の最小例は次のとおり。

```json
{
  "snapshot": {"number": 1, "slug": "initial", "label": "初期案", "note": "仮データ・保存なし"},
  "project": {"title": "依頼管理", "subtitle": "依頼を把握する"},
  "review_points": [{"number": 1, "title": "主な操作", "description": "登録の位置を確認する", "target_key": "primary-action", "status": "pending", "approval_history": []}],
  "fixed_annotations": [{"number": 1, "target_key": "primary-action", "padding_px": 8}],
  "screen_details": [{"number": 1, "key": "primary-action", "target_key": "primary-action", "region": "ヘッダー", "name": "登録", "type": "ボタン", "description": "登録を始める", "capability": "新規依頼を作れる", "behavior": "screen_transition", "trigger": "クリック", "result": "登録画面を表示", "failure": "移動失敗を通知"}],
  "requirements": {"purpose": ["依頼を把握する"], "target_users": ["担当者"], "confirmed": [], "hypotheses": [], "open_questions": [], "deferred": [], "next": []}
}
```

## 画面案の規則

- `snapshot.number` は1以上、`slug` と対象キーは小文字の kebab-case。確認ポイントの番号は過去案を含めて再利用せず、入力順にかかわらず表示は番号順とする。
- `snapshot.label` はレビュー UI の見出し、任意の `snapshot.note` は画面枠の外に表示する補足。案番号、仮データ、保存可否など制作・検証上の情報を TSX の画面内へ書かない。画面内の文言は利用者が実際の製品で見る情報と操作結果に限る。
- `review_points` は判断事項だけを件数制限なく含む。各項目の `status` は `pending`、`approved`、`reopened`。承認履歴があれば `approved` または `reopened` とし、履歴には最低限 `approved_in_snapshot` と当時の `title` を残す。追加指摘時は番号と履歴を維持し、`reopened` にする。
- `screen_details` は意味ある画面項目を網羅し、番号は確認ポイントと独立した1からの連番。処理種別は `screen_transition`、`backend_request`、`local_state_change`、`external_navigation`、`display_only` のいずれか。表示だけの項目も含め、装飾要素は除く。
- 対象要素に `data-review-target="キー"`、`data-screen-detail-target="キー"` を付ける。画面に描画される対象キーは各モード内で一意にし、同じ要素へ両方を付けてもよい。
- `fixed_annotations` を省略した場合、確認ポイントの対象要素に余白0で枠を置く。指定する場合は各 `number` が確認ポイントの番号と一致し、`target_key` と0～64の `padding_px` を指定する。旧案の割合座標を引き継ぐ場合だけ、`x_percent`、`y_percent`、`width_percent`、`height_percent` の4値を0～100で指定する。キーと割合座標は併用しない。
- 要件の7分類は文字列配列とし、未入力は空配列にする。各案を検証すると統合版 `discussion/requirements.md` が更新される。
- 確認ポイントや詳細設計が空なら、右パネルには入力待ちの表示を出す。画面案の TSX は空状態でも描画できるコンポーネントを export する。

## フィードバック

`discussion/NNN-slug-feedback.json` はサーバー受信かブラウザからのダウンロードで保存する。両経路は同じ形式を使う。

```json
{
  "schema_version": 1,
  "snapshot_id": "001-initial",
  "submitted_at": "2026-09-24T00:00:00.000Z",
  "items": [
    {"number": 1, "kind": "review_point", "status_at_render": "pending", "previously_approved": false, "reopened": false, "title": "主な操作", "approved": true, "comment": "", "target": null, "position": null},
    {"number": 2, "kind": "dom_annotation", "status_at_render": "pending", "previously_approved": false, "reopened": false, "title": "選択要素への指摘", "approved": false, "comment": "位置を変えたい", "target": {"selector": "[data-review-target=\"primary-action\"]", "target_key": "primary-action", "tag": "button", "text": "登録"}, "position": {"x_percent": 10, "y_percent": 20, "width_percent": 15, "height_percent": 5}}
  ],
  "screen_detail_feedback": [{"detail_key": "primary-action", "comment": "失敗時の通知を明確にする"}],
  "screen_details_approved": false,
  "general_comment": ""
}
```

`review_point` と `dom_annotation` は同じ番号空間を使う。追加指摘を削除した番号は再利用でき、`items` は常に番号順に保存する。追加指摘の `target` は DOM パス、任意の `target_key`、タグ、短い文言を含み、`position` は予備情報として扱う。次の案で対象を再び示す場合は DOM 情報を優先し、安定したキーへ変換する。`screen_detail_feedback` は `detail_key` で結び、項目別コメントと詳細設計全体の承認を分ける。承認済み項目へのコメントは同じ番号を `reopened` とし、過去承認を削除しない。
