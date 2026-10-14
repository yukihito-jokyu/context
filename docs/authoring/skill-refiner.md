---
title: skill-refiner — HTMLでスキルを検証・評価・改善する
sidebar_label: skill-refiner
---

# skill-refiner

既存スキル1つの成果物を題材ごとに作り、人間の指摘から評価基準と改善案を作ります。制作と評価には毎回新しい担当を使い、すり合わせから結果確認までHTMLで進めます。

## 渡す情報

スキル名1つ、そのスキルで行う題材1つ以上、必要な入力ファイル、作業領域を渡します。対象名が曖昧な場合は正本の場所を指定します。入力不足では実行を開始しません。

## 依頼例

```text
skill-refinerでexplain-htmlを検証・改善したいです。
題材は「備品貸出の仕組み」と「キャッシュが役立つ理由」です。
作業領域はskill-refiner-workspace/とし、指摘と承認はHTMLで行います。
```

## 進め方

1. HTMLで対象と題材を確認し、題材ごとに新規担当が成果物を作ります。
2. 成果物への指摘をHTMLで送信し、一般化した評価基準を確認・承認します。
3. 最初の成果物を新規担当が採点し、評価結果と具体的な改善案をHTMLで確認します。
4. 承認した修正を候補版に適用し、新規の制作担当と別の新規評価担当で再検証します。
5. 不合格なら逐次確認・最大3回の自動ループ・停止を選びます。合格候補は最後のHTML承認後に正本へ反映します。

## 成果物の例

独立担当が指定スキルを初期化し、入力確認のHTMLを保存した実出力です。人間の承認は未受領のため、制作・評価・改善は実行していません。

**到達点：入力確認HTML作成・人間の確認待ち。**

### 実行した依頼

```text
対象スキル /private/tmp/issue74-forward-target を、題材「キャッシュが役立つ理由を短く説明する」で検証・評価・改善したい。作業先は /private/tmp/issue74-forward-workspace とする。
```

### 成果物を取得する

- [実際の入力確認HTML](pathname:///examples/skill-refiner/review.html#download)
- [独立担当の検証報告HTML](pathname:///examples/skill-refiner/verification-report.html#download)
- [修正後の入力確認HTML](pathname:///examples/skill-refiner/review-v2.html#download)
- [修正後の独立検証報告HTML](pathname:///examples/skill-refiner/verification-v2.html#download)
- [実際のHTMLをブラウザで開く](pathname:///examples/skill-refiner/review.html)
- [実行入力の原本](pathname:///examples/skill-refiner/input.md#download)
- [実行・検証記録（JSON）](pathname:///examples/skill-refiner/execution.json#download)

### 確認した結果

- 対象スキルと固定版のハッシュ一致を確認。新規の制作・評価担当は起動していない。
- localhostの起動はサンドボックス制約で失敗。オフラインHTMLの生成は成功。
- 初回実行で入力ファイルを置いた作業領域の初期化問題を発見。保存した独立報告は修正前の観測であり、その後コードを修正して回帰テストを追加した。
- この例のブラウザ表示・操作と、対象スキルの品質評価は未実施。
- 修正後、新規の独立担当が入力を作業領域内に保存して初期化し、HTMLの入力確認待ちまで到達した。承認・指摘は補作していない。

## 確認するポイント

ページの初期値や無回答は承認になりません。送信した指摘は、表示した版・題材・評価基準と結び付けて保存します。制作担当へは検証用スキルのメタ知識を含めず、評価担当は制作担当を再利用しません。

HTMLサーバーはlocalhostで動作し、送信を保存します。サーバーが利用できない場合は、オフラインHTMLから回答をコピー・保存して共有します。hooksは実行前の工程検査を追加するもので、設定を置いただけでは実環境での制止を証明できません。

## hooks付き配布

このリポジトリでは、専用の生成処理でCodex用とClaude Code用の配布物を作れます。

```sh
python3 utils/plugins/skill-refiner/build.py --agent codex --output /tmp/skill-refiner-codex
python3 utils/plugins/skill-refiner/build.py --agent claude-code --output /tmp/skill-refiner-claude
```

生成物は正本から作り、手動編集しません。公開・導入・ユーザー設定へのhooks登録は別の操作です。[Skillとpluginの配布・導入](plugin-distribution.md)も参照してください。

## 正本を読む

詳細な操作、評価結果の形式、hooksの制約は[skill-refinerのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/authoring/skill-refiner/SKILL.md)を参照してください。
