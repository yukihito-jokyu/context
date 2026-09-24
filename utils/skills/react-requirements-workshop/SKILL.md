---
name: react-requirements-workshop
description: 曖昧な React UI 構想を、動く画面案とフィードバックの反復で要件へ変える。画面を見ながら議論したい、React の案を履歴に残したい、Design System に沿って画面要件を固めたい場合に使う。
---

# React UI 要件すり合わせ

## 最初の対話

「誰が使うか」「その人が何を達成したいか」「最初に確かめる画面・操作」を1〜3問で聞く。不明な回答は仮説として記録する。ユーザーが画面案を求めるまではアプリを作らず、分かったことと画面で確認したい論点を短く返す。

## 作業領域を作る

保存先指定がなければ利用プロジェクト内に `react-discussion-<短いkebab-case名>/` を作る。同名の領域があれば既存議論か新規か確認する。初回だけ次を実行する。アプリ、依存関係、レビュー UI、サーバーは作業領域に一組だけ置く。

```sh
python3 <skill-dir>/scripts/init_workspace.py --workspace <workspace>
(cd <workspace> && npm install)
```

別セッションで再開するときは、`discussion/snapshot-hashes.json`、`discussion/requirements.md`、最新の `discussion/NNN-slug.json` とフィードバック、`src/main.tsx` を先に読む。既存のアプリを初期化し直さず、保存されたファイルから続ける。

## 画面案を作る

1. 画面の作成・変更前に同梱の [Design System Skill](vendor/design-system/SKILL.md) を読む。主 Pattern、操作 Pattern、部品、個別 Example、Token、検証手順を順に確認する。`components.json` の `@yukihi` Registry から必要な項目だけ `npx shadcn@latest view/add @yukihi/<item>` で導入する。
2. [入力形式](references/input-schema.md) と [レビュー規則](references/review-guidelines.md) に従い、`src/snapshots/NNN-slug.tsx` と `discussion/NNN-slug.json` を追加する。TSX は default export とし、確認ポイント・画面詳細設計の対象へ安定した DOM キーを付ける。過去の TSX と JSON は上書きしない。
3. 確認ポイントはユーザー判断が必要なものだけにし、件数で打ち切らない。画面詳細設計は意味のある全項目について、表示・操作・処理種別・結果・失敗時を記録する。承認済み項目の番号・履歴・内容を維持し、指摘があった項目だけ `reopened` とする。
4. `src/main.tsx` の TSX と JSON の import を同じ案へ切り替える。次の順に検証・保存する。実ブラウザ検証には作業領域の `agent-browser` を使用し、必要なら `npx agent-browser install` でブラウザを用意する。

```sh
python3 <skill-dir>/scripts/validate_snapshot.py --workspace <workspace> --snapshot NNN-slug
(cd <workspace> && npm run typecheck && npm run lint)
python3 <skill-dir>/scripts/freeze_snapshot.py --workspace <workspace> --snapshot NNN-slug
# 起動済みの Vite URL を --url に指定する。起動していない場合だけ npm run dev を一度起動する
python3 <skill-dir>/scripts/verify_rendered_annotations.py --workspace <workspace> --snapshot NNN-slug --url <vite-url> --output <workspace>/discussion/verification/NNN-slug.json --screenshot-dir <workspace>/discussion/verification/NNN-slug-screenshots
```

`freeze_snapshot.py` は production build を行い、その時点の表示一式を `discussion/rendered/NNN-slug.zip` に保存する。ソースの履歴は TSX と JSON、実際に見せた画面の履歴はこの zip で保持する。共通 UI や Design System 部品が後に変わっても、過去案は次のコマンドで別セッションから閲覧できる。生成済みの zip、TSX、JSON を直接編集しない。

レビュー UI は画面案を「画面案」ラベル付きの枠内に表示する。画面案が白や淡色でも外側と区別できる余白・背景差・枠線を維持し、`verify_rendered_annotations.py` の `frameSeparated` とスクリーンショットで確認する。レビュー UI の CSS は画面案内の Design System 部品へ波及させない。
案番号や「仮データ」「保存なし」など議論用の補足は `snapshot.label`・`snapshot.note` に記録して画面枠の外へ表示する。スナップショット TSX の画面内は製品利用者に見せる内容だけにする。

```sh
python3 <skill-dir>/scripts/serve_snapshot.py --workspace <workspace> --snapshot NNN-slug
```

検証が失敗した場合は原因を修正して再検証する。まだ提示していない現在案の修正と、提示済みの過去案の改変を区別し、提示済み案の修正は新しい番号の案として保存する。

## ユーザーに確認してもらう

画面案を切り替える前に、この作業領域の Vite とフィードバック受信サーバーが既に動いているか確認する。Vite が動いていれば同じ URL とポートを使い続け、スナップショットごとに再起動したり別ポートを開いたりしない。起動していない場合だけ `npm run dev` を一度実行する。実ブラウザ検証には実際の URL を `--url` で渡す。

フィードバック受信サーバーも、現在のスナップショットに対応して動いていれば再起動しない。受信サーバーはスナップショットを固定して起動し、送信を1件保存すると終了する。別の案に切り替わった場合や終了後は、サーバー保存が必要なときだけ `python3 <skill-dir>/scripts/serve_review.py --workspace <workspace> --snapshot NNN-slug --review-url <vite-url>` を起動する。再起動せず確認を進める場合は、送信時にダウンロードされるフィードバック JSON を使う。受信先ポートを変える必要があるときだけ `REVIEW_RECEIVER_PORT` と `serve_review.py --port` を同じ値にする。送信ボタンだけで終了済みの AI ターンが再開するとは説明しない。

確認ポイントと画面詳細設計を別モードで示す。確認ポイントには承認履歴と追加指摘、画面上の要素選択による指摘を含める。選択した要素は番号付きカードとして追加し、コメント、承認、削除ができる。詳細設計には項目コメントと全体承認を置く。対象要素と枠の位置、モード切替、スクロール、番号からコメント欄への移動を実ブラウザで確認する。

受信サーバーに接続できない場合、送信操作で `NNN-slug-feedback.json` がダウンロードされる。ユーザーにそのファイルを `<workspace>/discussion/` へ置いてもらい、受領後に読む。

## フィードバックを反映する

`discussion/NNN-slug-feedback.json` を読み、確認ポイント、画面内で追加した指摘、詳細設計コメント、全体コメントを番号と対象キーに結び付ける。承認済み事項は確定要件へ、未確定事項は仮説・未決事項へ反映する。追加指摘がある承認済み項目は履歴を消さず同じ番号の `reopened` にする。修正後に再承認されたら履歴を追加する。ユーザーが変更を求めていない箇所は維持する。複数の解釈で画面が大きく変わる場合だけ、1問で確認する。結果を新しい JSON、TSX、`discussion/requirements.md` へ同期する。

全確認ポイントと追加指摘が承認され、詳細設計も承認された場合だけ、承認結果を反映した新しい JSON を `--requirements-input` に渡して保管する。コメントは承認結果の解釈に反映したうえで残す。

```sh
python3 <skill-dir>/scripts/archive_approved.py --workspace <workspace> --snapshot NNN-slug --requirements-input <workspace>/discussion/MMM-feedback-applied.json
python3 <skill-dir>/scripts/validate_approved.py --workspace <workspace>
```

承認済み TSX は `src/approved/`、承認記録と統合要件は `discussion/approved/` に保存する。保管済み TSX、元案、メタデータ、フィードバック、要件入力のハッシュを検証する。

## 反復を終える

ユーザーが終了を伝えるまで画面提示、指摘、修正を繰り返す。終了時は最終画面、最終要件、承認済み画面と要件、確定事項、未決事項、過去案の場所を簡潔に案内する。本番実装や公開は別依頼として扱う。
