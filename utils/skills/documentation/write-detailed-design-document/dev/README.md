# このスキルを保守する

`spec.json`はルールと出力契約の正本である。`SKILL.md`の「2. 手順」、`scripts/design.py`、`references/design-guide.md`と見本は手で保守し、それ以外の生成部分はskill-foundationのrender_skill.pyで更新する。

## 検査の範囲と実行

このディレクトリの検査は詳細設計書作成スキルだけを対象とする。リポジトリ全体のtestsへ混在させない。リポジトリルートで、skill-foundationが`.agents/skills/skill-foundation`にある場合は次を実行する。

```sh
python3 .agents/skills/skill-foundation/scripts/render_skill.py --dir utils/skills/documentation/write-detailed-design-document
python3 .agents/skills/skill-foundation/scripts/eval_check.py utils/skills/documentation/write-detailed-design-document
python3 .agents/skills/skill-foundation/scripts/probe.py utils/skills/documentation/write-detailed-design-document
python3 .agents/skills/skill-foundation/scripts/skill_lint.py utils/skills/documentation/write-detailed-design-document --phase 5
```

skill-foundationが別の場所にある場合は、その部分だけを置き換える。通常の設計書作成ではskill-foundationを呼ばず、このスキル自身のscripts/run.pyとscripts/design.pyを使う。

`probes.json`は検査に通る見本、機械で拒否する違反例、意味を読んで検出する4種類の違反例を持つ。意味の違反例は構造検査を通るように作り、誤って別の機械検査に依存しないことも確認する。

## 価値と独立実行

`eval/eval.json`は利用者と確認した6つの価値（既存3つと保存先・図・参照の3つ）、10分野の判定窓（境界は5ページへ分割し、計14窓）と成功・失敗例を持つ。各窓は元の基準を分割したものであり、全窓の通過を求める。判定資料はreview.htmlの各節を使い、途中で省略されずに渡るかも確かめる。

`evals.json`の通常・既定値・不一致と未検証の3題材で測り、最後に別分野の予約題材を加える。`fixtures/basic`を一時プロジェクトの元とし、題材の違いはsetupで作る。収束テストの起動、独立した担当の記録の分析、最後のレビュー検出率はskill-foundationの手順に従う。

`results/`と`convergence-report.md`は操作の絶対パス等を含むため共有しない。再測定した人が手元で作る。元の判定を都合よく合格へ書き換えず、変更点と利用者の回答を記録して次の独立実行で確認する。

## 採点前の境界入力の準備

型と状態の定義を省略せず渡すため、境界は契約・項目・状態へ分ける。`eval/prepare_inputs.py`は既存のdesign.jsonを読み取り専用で変換し、一時プロジェクトの`.skill-runs/_fence/eval-inputs/`へ派生HTMLと原本ハッシュ付きのmanifestを置く。判定結果や推奨の回答は作らない。項目の和集合と値を元データへ戻して照合し、各分類の全境界がちょうど一つのページに載ることを検査する。原本11ファイルは変えない。

独立生成が終わり、diffで採点する前に、各一時プロジェクトについて次を実行する。

```sh
python3 utils/skills/documentation/write-detailed-design-document/dev/eval/prepare_inputs.py stage --project <一時プロジェクト>
python3 utils/skills/documentation/write-detailed-design-document/dev/eval/prepare_inputs.py check --project <一時プロジェクト>
```

`input-pages.json`のページ数とEvalの判定先は一緒に保守する。現在は契約1・項目2・状態2ページで、全窓の通過を求める。空の割当ページも理由を表示し、原本にある境界を欠落させないことをmanifestの検査で保証する。11,000文字以内に収まらない、登録したページ数を超える、原本と派生物が違う場合は採点を始めず止める。入力分割の変更は確認基準を維持し、利用者と合意して行う。`plan --project ...`はページ数の候補を計算するだけで、Evalを自動的に書き換えない。

派生物は評価基盤が計測から除外する一時資料の領域に置く。fenceの設定・lab.json・ログは変更せず、配下のeval-inputsだけを使う。派生物が出力の一致度へ混ざらないこともdiffの内訳で確認する。


## 項目の図と参照先の抜粋

presentation.pyは各項目の図と抜粋、PNGの個別変換を担当する。design.py readは値を削らない分野別ページ、sheetsは既存のPuppeteerによる確認画像を生成する。QA画像の一覧を開いたことと、必要な図を拡大して読んだことを実行記録に分ける。

レンダラーを変えたときはdev/refresh_review_fixtures.py <本体>でレビューの見本を再作成する。意味の違反はdev/probes.jsonの各design.jsonを正本とし、画像と文書を実際に生成する。PNGのバイトの決定性を仮定せず、各見本のPNG・MMD・manifest全組をcontent hashで保存する。検査を弱めて古い見本を通さない。

図の内容と読みやすさ、参照の必要条件はeval/presentation-review.jsonのPV-1/PV-2で独立評価する。全PNG一覧と必要な原画像、全Markdownを実際に読み、元出力のハッシュを保存する。形式検査18件の合格とは別に集計し、両ラウンドに同じ基準を適用する。

OUT-17の引用削除probeは、生成後の手書き編集を拒否するOUT-06も同時に検知する。保護を緩めず、重複検知の警告を残す。図と参照の改善測定は独立レビューの記録を含め、従来の4ラウンドと分けて報告する。
