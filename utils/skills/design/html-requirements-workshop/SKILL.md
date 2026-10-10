---
name: html-requirements-workshop
description: 要件、やりたいこと、画面像が曖昧なユーザーと、質問・HTMLモック・自然言語フィードバックを反復して目的と画面要件を固め、経緯をスナップショットと要件Markdownへ残す。ユーザーが「何を作るかまだ決まっていない」「画面を見ながら考えたい」「HTMLモックで擦り合わせたい」「UI案を試しながら要件を整理したい」と述べた場合、またはプロダクトや業務画面の構想が曖昧で対話的な可視化が役立つ場合に使用する。確定済み仕様の本番実装や、単発の完成HTML制作だけが目的の場合には使用しない。
---

# HTML要件すり合わせ

曖昧な構想を急いで仕様へ固定せず、ユーザーが見て指摘できるHTMLと、AIが管理する要件記録を往復しながら具体化する。

## 最初の対話

最初は、ユーザーが答えやすい質問を1〜3問だけ行う。最低限、次の順で把握する。

1. 誰が使うか
2. その人が何を達成したいか
3. 最初に確かめたい画面または操作は何か

答えが曖昧でも追加質問を重ねすぎない。「まだ分からない」を有効な回答として扱い、仮説として記録する。

ユーザーがHTMLモック作成を求めるまでは、HTMLを生成しない。会話で分かったことを短く要約し、モックで確認すると有効な論点を提案する。

## 作業領域

ユーザーが保存先を指定しない場合、現在のプロジェクトに`html-discussion/`を作る。

```text
html-discussion/
├── inputs/
│   ├── 001-initial.json
│   └── 002-feedback-applied.json
├── runs/
│   ├── run-001/
│   └── run-002/
├── approved/
│   ├── requirements.md
│   └── approved-001-run-002-feedback-applied.html
├── verification/
│   ├── run-001/
│   └── run-002/
└── feedback/
    ├── run-001/
    │   └── feedback.json
    └── run-002/
```

各`run-NNN/`は次を含む。

```text
run-NNN/
├── mockups/NNN-slug.html
├── requirements.md
├── mock-index.html
├── artifact-map.md
├── validation.json
└── manifest.json
```

過去の入力、run、feedbackを上書きしない。修正は新しい入力とrunで行う。生成後のrunをAIが直接編集してはならない。問題があれば入力、テンプレート、またはスクリプトを直して新しいrunを生成する。

`approved/`は承認済み画面を通常のrun列から見分けるための領域である。承認済みHTMLは`approved-NNN-run-NNN-slug.html`として直下へ追加し、過去のHTMLを上書きしない。`requirements.md`だけは1ファイルに保ち、承認のたびに目的、対象ユーザー、承認済み要件の最新統合内容へ更新する。仮説、未決事項、見送った案、次の確認事項、承認元ファイル名は書かない。それ以外のファイルを`approved/`へ置かない。

## 入力を作る

モック作成の依頼を受けたら、[references/input-schema.md](references/input-schema.md)に従って`inputs/NNN-slug.json`を作る。

AIが担当するのは次だけである。

- 左側へ入れる具体的な画面断片`mock_html`
- ユーザー判断が必要な確認ポイント`review_points`。件数は固定せず、必要な項目だけを選ぶ
- 画面内の意味のある全項目を扱う件数制限なしの`screen_details`
- 会話から得た要件、仮説、未決事項
- AIが用意する確認対象をDOMへ紐付ける`target_key`、または旧runのユーザー範囲指摘を引き継ぐ割合座標

`review_points`では画面詳細の説明を繰り返さず、選択肢や未確定事項などユーザー判断が必要なものを自由な件数で選ぶ。過去に承認された項目は`status`と`approval_history`を維持して次の入力へ引き継ぐ。新規項目は過去番号を再利用せず次の番号を割り当てる。承認済み項目への追加指摘は、承認履歴と番号を残したまま`reopened`として次のrunへ反映する。

`screen_details`では、各項目が何を表示するか、何ができるか、操作のきっかけ、画面遷移・バックエンド通信・画面内変更などの処理種別、結果、失敗時を記述する。装飾DOMは除き、対象へ`data-screen-detail-target`を付ける。

認知負荷と指摘負荷を抑えるため、入力を作る前に[references/mock-guidelines.md](references/mock-guidelines.md)を読む。

## スナップショットを生成する

次を実行する。`<skill-dir>`はこの`SKILL.md`があるディレクトリ、`<workspace>`は`html-discussion/`である。

```bash
python3 <skill-dir>/scripts/generate_snapshot.py \
  --input <workspace>/inputs/NNN-slug.json \
  --template <skill-dir>/assets/mock-shell.html.tpl \
  --output <workspace>/runs/run-NNN
```

環境がコマンドラッパーを要求する場合は、その規則に従う。

生成後、次を実行する。

```bash
python3 <skill-dir>/scripts/validate_workspace.py \
  --run <workspace>/runs/run-NNN
```

検証が失敗したらrunを直接直さない。原因となる入力またはスキル側ファイルを修正し、新しいrunへ生成する。

AIが用意した`target_key`注釈があり、ChromeまたはChromiumを利用できる場合は、実ブラウザでも検証する。検証結果と画像はrunを変更しないよう`verification/run-NNN/`へ保存する。

```bash
python3 <skill-dir>/scripts/verify_rendered_annotations.py \
  --run <workspace>/runs/run-NNN \
  --output <workspace>/verification/run-NNN/browser-validation.json \
  --screenshot-dir <workspace>/verification/run-NNN/screenshots
```

`browser-validation.json`では複数画面幅の`alignment`と`scroll_alignment`がすべて`valid`、`annotation_errors`と`unapproved_nested_scroll_count`がすべて`0`であることを確認する。さらに`fixed_annotation_hit_test`、`dom_annotation_hit_test`、`number_badge_hit_test`、`annotation_mode_number_pass_through`がすべて`true`であることを確認し、固定枠とユーザー追加枠の面が背後のモック操作を妨げず、番号だけが通常時のコメント移動操作となり、注釈モードでは番号も対象選択を妨げないことを保証する。`allowed_nested_scroll_count`が1以上の場合は、そのスクロール自体が確認対象であり、対応する要素に`data-allow-nested-scroll`が付いていることを確認する。画像を閲覧できる場合は、左側の縦スクロールが外枠の1本だけであること、対象の選択が意味的に正しいこと、番号ラベルが主要情報を隠していないことも確認する。位置の正否は画像の印象ではなくブラウザ座標の結果で判断する。

`screen_details`がある場合は同じ検証で`screen_detail_alignment`が`valid`、詳細設計件数と番号順が入力と一致し、確認ポイントの青枠と詳細設計の赤枠がモードごとに分離されることを確認する。詳細設計中はDOM指摘ボタンが非表示で、連番・枠の表示切替、項目コメント、全体承認、確認ポイントへ戻した後の分離がすべて成功していることを確認する。

## ユーザーに確認してもらう

右パネルには「確認ポイント」と「画面の詳細設計」を切り替える操作を表示する。「今回の確認ポイント」という表現は使わない。確認ポイントではLLMが選んだ自由な件数の項目、承認履歴、DOM選択による指摘を扱い、画面詳細設計では全項目を扱う。承認履歴がある項目も青枠と連番を通常どおり表示し、追加指摘を入力できるようにする。詳細設計中は「要素を選んで指摘」を表示しない。両モードのコメントは同じ送信で保存するが、`items`と`screen_detail_feedback`へ分離する。

ローカルサーバーを使える場合、次を起動してツールの実行セッションを待機させる。

```bash
python3 <skill-dir>/scripts/serve_review.py \
  --run-dir <workspace>/feedback/run-NNN \
  --mock-dir <workspace>/runs/run-NNN/mockups \
  --mock-file NNN-slug.html
```

表示された`REVIEW_URL`をユーザーへ渡す。ユーザーが送信すると`feedback/run-NNN/feedback.json`が保存され、サーバーは終了する。Codexが同じターンで待機していれば、受信後すぐ読み取る。

サーバー起動が許可されない環境では、生成HTMLを直接渡す。送信時にダウンロードされるJSONをユーザーにワークスペースへ置いてもらい、完了連絡を受けてから読む。HTMLのボタンだけで終了済みのAIターンを再開できるとは説明しない。

## フィードバックを反映する

`feedback.json`を読み、次の順で処理する。

1. 承認済み項目を確定要件へ移し、番号、`status`、`approval_history`を次の入力へ引き継ぐ。
2. 自然言語コメントを、対象番号と結び付けて要件・仮説・未決事項へ反映する。
3. `screen_detail_feedback`を`detail_key`で対応する詳細設計へ結び付け、画面項目の役割、処理種別、遷移先、通信内容、結果、失敗時へ反映する。
4. ユーザーのDOM注釈は`target.selector`、`target.target_key`、`target.tag`、`target.text`から対象を判断し、`position`は確認用の予備情報として扱う。旧runの範囲注釈だけは割合座標から判断する。
5. 承認済み項目への追加コメントは過去承認を削除せず、同じ番号の`reopened`項目として次の入力へ反映する。修正版が再承認されたら履歴を追加して`approved`へ戻す。
6. 判断が一意なら次の入力へ反映する。複数の解釈で画面が大きく変わる場合だけ、1問で確認する。
7. 前回の承認済み内容を維持し、変更要求がない箇所を不用意に作り直さない。
8. 承認結果を反映した新しい入力を作る。
9. `feedback.json`の全項目が`approved: true`で、詳細設計がある場合は`screen_details_approved: true`でもあるとき、承認元run、feedback、新しい入力を使って次のコマンドを実行する。いずれかが未承認なら保管せず、次の修正runへ進む。

```bash
python3 <skill-dir>/scripts/archive_approved_mock.py \
  --run <workspace>/runs/run-NNN \
  --feedback <workspace>/feedback/run-NNN/feedback.json \
  --requirements-input <workspace>/inputs/MMM-feedback-applied.json \
  --approved-dir <workspace>/approved
```

承認処理はrunのmanifestとHTMLのチェックサムを照合し、同じrunの二重登録、未承認項目、不正な入力を、既存の承認物を変更せず拒否する。成功後、検証結果を`approved/`の外へ保存する。

```bash
python3 <skill-dir>/scripts/validate_approved_mock.py \
  --approved-dir <workspace>/approved \
  --source-run <workspace>/runs/run-NNN \
  --requirements-input <workspace>/inputs/MMM-feedback-applied.json \
  --output <workspace>/verification/approved/run-NNN.json
```

10. すり合わせを続ける場合は、新しい入力から次のrunを生成する。

要件MarkdownはAIが会話から管理する記録である。最低限、目的、対象ユーザー、確定した要件、仮説、未決事項、見送った案、次に確認することを毎回同期する。

## 反復を終える

ユーザーが「終了」「ここまで」「十分」「この案で進める」などと伝えるまで、質問、生成、確認、反映を繰り返す。

終了時は次を簡潔に渡す。

- 最終runと最終HTMLへのリンク
- 最終`requirements.md`へのリンク
- `approved/`に保存した承認済みHTMLと統合`requirements.md`へのリンク
- 確定事項と未決事項
- 保存された過去runの場所

本番アプリの実装、外部への公開、デプロイは、このスキルの反復に含めない。ユーザーが別途依頼した場合にのみ進める。
