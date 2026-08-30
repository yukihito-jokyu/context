# 入力JSON

生成スクリプトは次の構造を受け取る。

```json
{
  "schema_version": 1,
  "snapshot": {
    "number": 1,
    "slug": "initial",
    "label": "初期案"
  },
  "project": {
    "title": "依頼管理画面",
    "subtitle": "チームの依頼を把握する"
  },
  "mock_html": "<section class=\"app-view\"><button data-review-target=\"primary-action\" data-screen-detail-target=\"primary-action\">新規登録</button></section>",
  "review_points": [
    {
      "number": 1,
      "title": "主な操作",
      "description": "登録操作の位置と言葉を確認します。",
      "status": "pending",
      "approval_history": []
    }
  ],
  "fixed_annotations": [
    {
      "number": 1,
      "target_key": "primary-action",
      "padding_px": 8
    }
  ],
  "screen_details": [
    {
      "number": 1,
      "key": "primary-action",
      "target_key": "primary-action",
      "region": "ヘッダー",
      "name": "新規登録",
      "type": "ボタン",
      "description": "新しい依頼の登録を始める。",
      "capability": "登録画面を開ける。",
      "behavior": "screen_transition",
      "trigger": "クリック",
      "result": "新規登録画面へ移動する。",
      "failure": "移動できない場合は再試行できるエラーを表示する。"
    }
  ],
  "requirements": {
    "purpose": ["チームの依頼状況を把握する"],
    "target_users": ["依頼を受け付ける担当者"],
    "confirmed": [],
    "hypotheses": ["新規登録が最も多い操作である"],
    "open_questions": ["依頼元を一覧に表示するか"],
    "deferred": [],
    "next": ["登録操作の位置を確認する"]
  }
}
```

## 規則

- `schema_version`は`1`にする。
- `snapshot.number`は1以上の整数にする。
- `snapshot.slug`は小文字のkebab-caseにする。
- `review_points`はユーザー判断が必要な項目だけを含め、件数を制限しない。画面詳細設計の説明を繰り返すためには使わない。
- 各確認ポイントは`number`、`title`、`description`を持つ。`status`は`pending`、`approved`、`reopened`のいずれかで、省略時は旧入力互換のため`pending`とする。
- `approval_history`は配列とし、新規項目では空、`approved`と`reopened`では過去承認を1件以上保持する。各履歴は少なくとも`approved_in_snapshot`と、その時点の`title`を持つ。
- 承認済み項目への追加指摘は番号と`approval_history`を変えず、`status: reopened`と`latest_feedback`を設定する。修正版の再承認後は履歴を追加して`approved`へ戻す。
- 過去に使った番号を新規項目へ再利用せず、既存番号の最大値に1を加える。入力順にかかわらず生成時に番号順へ整列される。
- `screen_details`は任意の配列で、件数を制限しない。画面内の意味のある表示・操作単位を網羅し、装飾だけのDOM要素は含めない。
- 各詳細設計は`number`、`key`、`target_key`、`region`、`name`、`type`、`description`、`capability`、`behavior`、`trigger`、`result`、`failure`を持つ。
- 詳細設計の`number`は1からの連番、`key`と`target_key`は一意な小文字kebab-caseにする。入力順にかかわらず番号順へ整列される。
- `behavior`は`screen_transition`、`backend_request`、`local_state_change`、`external_navigation`、`display_only`のいずれかにする。
- 詳細設計の対象要素へ`data-screen-detail-target="キー"`を付け、`target_key`から1対1で参照する。同じ要素が確認ポイントでもある場合は`data-review-target`と併記できる。
- `fixed_annotations`の番号は重複させず、対応する`review_points`の番号と一致させる。
- AIが最初から置く注釈は、`mock_html`の対象へ`data-review-target="キー"`を付け、`fixed_annotations.target_key`から参照する。キーは小文字のkebab-caseで一意にする。
- `padding_px`は対象要素から枠までの余白で、0〜64を指定する。省略時は8になる。
- 旧runでユーザーがドラッグした範囲を引き継ぐ場合だけ、互換形式の`x_percent`、`y_percent`、`width_percent`、`height_percent`を使う。値は0〜100でキャンバス内に収める。新しいユーザー指摘はDOM選択として送信されるため、次の入力では対象要素へ`data-review-target`を付け、`target_key`へ変換する。
- 1つの注釈へ`target_key`と割合座標を同時に指定しない。
- `mock_html`は信頼済みの静的HTML断片に限定する。
- `script`、`iframe`、`object`、`embed`、`javascript:`、`on*`イベント属性を含めない。
- 要件の各値は文字列配列にする。未入力は空配列にする。

`mock_html`が空の場合、生成物は「画面内容の入力待ち」を表示する。`review_points`が空の場合、右側は確認ポイントの空状態を表示する。確認ポイントが4件以上でも削除や打ち切りを行わない。`screen_details`がない旧入力、または空配列の場合、「画面の詳細設計」には空状態を表示する。

## 対象要素へ追従する注釈

```html
<button data-review-target="primary-action">新規登録</button>
```

```json
{
  "number": 1,
  "target_key": "primary-action",
  "padding_px": 8
}
```

生成HTMLは表示時に対象要素の実座標を計測するため、画面幅や内容の高さが変わっても枠が追従する。

画面詳細設計は別の属性で紐付ける。

```html
<button
  data-review-target="primary-action"
  data-screen-detail-target="primary-action"
>
  新規登録
</button>
```

フィードバックの確認ポイントには`status_at_render`、`previously_approved`、`reopened`を保存する。承認済み項目への追加指摘は`previously_approved: true`、`reopened: true`、`approved: false`となる。再確認中の修正版を再承認した場合は、過去承認を維持したまま`approved: true`となる。

フィードバックでは既存の`items`と分離して、詳細設計へのコメントを`screen_detail_feedback`、画面詳細設計全体の承認を`screen_details_approved`へ保存する。詳細設計項目ごとの承認操作は設けない。
