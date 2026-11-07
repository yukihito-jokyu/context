# 調査記録

## 依頼と確認した価値

- 確認方法：依頼本文とdev/eval/eval.jsonのtalk-1〜talk-4を確認（2026-11-06）。
- 確認の状態：確認済み
- 分かったこと：基本設計の言い換えを避け、実装・試験へ渡せる境界、状態、保存、競合、回復を具体化する。製品固有条件は入力資料から読み取る。事例8件と収束テストの題材4件に利用者の同意がある。
- 使ったルール：IN-01、IN-02、STEP-01、STEP-02、STEP-05、OUT-02、OUT-03、OUT-10、OUT-11、OUT-12

## 判定入力の分割

- 確認方法：skill-foundationのscripts/eval_check.pyにあるMODEL_TEXT_MAXと、収束テスト1回目の判定記録を確認（2026-11-06）。talk-4で修正案を利用者と確認した。
- 確認の状態：確認済み
- 分かったこと：判定入力は12,000文字までであり、長いdesign.jsonの後半が省略される。3つの価値と元の成功・失敗例を維持し、分野別の10判定へ分けた。HTMLの節は台帳の値を要約せずに生成し、機械検査の同一性確認に含める。初回6出力から生成した各判定窓が上限内に収まることを確認した。全体の設計が大きい場合の無制限な評価入力を保証するものではない。
- 使ったルール：STEP-03、OUT-01、OUT-06、OUT-07

## agent2agentの要件と基本設計

- 確認方法：指定されたローカル資料の本文を確認（2026-11-06）。記載を確認したことと、採用・実装・実機検証を区別した。
- 確認の状態：確認済み
- 分かったこと：
  - [原資料basic-design.mdの3行目](eval/inputs/agent2agent/basic-design-excerpts.md#L7)は「記載する設計案は、採用承認を示すものではない。」と定める。
  - [原資料basic-design.mdの265行目](eval/inputs/agent2agent/basic-design-excerpts.md#L11)は保存後の受付応答と本文・返却結果の非永続化を記す。
  - [原資料basic-design.mdの283行目](eval/inputs/agent2agent/basic-design-excerpts.md#L15)と[原資料basic-design.mdの308行目](eval/inputs/agent2agent/basic-design-excerpts.md#L19)は保存と競合の具体化を要する。
  - [原資料basic-design.mdの534行目](eval/inputs/agent2agent/basic-design-excerpts.md#L27)は「判断時点で未回答かつ期限前かを保存側で確認し、最初の有効な判断だけを確定する。」と記す。
  - [原資料basic-design.mdの955行目](eval/inputs/agent2agent/basic-design-excerpts.md#L43)は要求・応答、物理列・索引・移行、排他・期限、画面操作を具体化する対象として挙げる。
  - [原資料basic-design.mdの663行目](eval/inputs/agent2agent/basic-design-excerpts.md#L31)と[原資料requirement.mdの461行目](eval/inputs/agent2agent/requirement-excerpts.md#L11)は一致していない。変更記録を根拠にしつつ、未反映の受入条件まで整合済みとは扱わない。
  - [原資料requirement.mdの584行目](eval/inputs/agent2agent/requirement-excerpts.md#L15)は対象、変更前後、理由、影響を求める。
  - [原資料basic-design.mdの930行目](eval/inputs/agent2agent/basic-design-excerpts.md#L35)は採用版、復元、権限継承、画面再表示を含む。本作業で実機検証はしていない。
- 使ったルール：IN-02、STEP-01、STEP-02、OUT-10、OUT-11、OUT-12
- 入力の識別：requirement.md、SHA-256 `55eb31ff62bd0b974a1423b75a49dd528653da23afd0f55072a703d81ab94f12`、584行。
- 入力の識別：basic-design.md、SHA-256 `b71580b261460842d1dfc9ab3975efae2fe3a853d0713d9865097a76952342cf`、1299行。

## リポジトリの文章と正本管理

- 確認方法：AGENTS.md、projects/context/AGENTS.md、utils/skills/authoring/skill-authoring/SKILL.mdを確認（2026-11-06）。
- 確認の状態：確認済み
- 決まり：AGENTS.md。「Skill の正本は `SKILL.md` とし、README は要約カタログとして扱います。」ユーザーのAGENTS.md指示は、根拠の実際の記述と絶対パス・行番号リンクを求める。
- 分かったこと：共通スキルはutils/skillsに置く。公開例は更新後のスキルを独立したサブエージェントで実行して作る。利用者はhooksをプロジェクト設定に登録すると明示したため、今回はその選択を適用する。
- 使ったルール：OUT-09

## 共通ランタイムとローカルの実行環境

- 確認方法：skill-foundationのreferences/runtime.md、references/platforms.md、init_skill.pyの実行結果とコピーされたscriptsを確認（2026-11-06）。
- 確認の状態：確認済み
- 分かったこと：start/check/finish、hooks、指摘収集は生成された共通ランタイムを使う。追加の製品APIやイベントは使わない。固有の処理はPython標準ライブラリによる資料一覧、引用照合、JSON検査、MarkdownとHTMLの生成に限定する。Mermaidはフェンス付きの記述として出力し、実行基盤の製品仕様は固定しない。
- 使ったルール：STEP-03、STEP-04、OUT-01、OUT-04、OUT-05、OUT-06、OUT-07、OUT-08
- 実行環境：ローカルのPythonとgitの起動を確認した。個人の環境に依存する版の出力は公開資料へ含めない。

## 境界の評価入力の分割

- 確認日：2026-11-07。
- 出典：利用者のtalk-5回答「はい」、dev/eval/prepare_inputs.pyとinput-pages.json、作成元eval_check.pyの表示文字の数え方。
- 確認の状態：4回目の8原本を変更せず、境界の全項目の和集合と各値、各分類の全境界の被覆、原本SHA-256を検査した。最大10,815文字であり、評価器の12,000文字上限を下回る。
- 採用する方式：型と状態を含む境界を契約・項目・状態へ分け、合計5ページで同じ基準を確認する。他の9分野は元の窓を使い、計14窓の全通過を求める。
- 限界：文書の正しさの判定結果ではない。採点前の入力の網羅性の検査である。
- 使ったルール：STEP-05、OUT-10、OUT-11。
