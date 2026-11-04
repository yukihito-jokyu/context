# 基本設計スキルの調査

## 利用者と確かめた価値

- 確認方法：Issue #102とdev/eval/eval.jsonのtalk-1〜talk-4（2026-11-04）。
- 確認の状態：確認済み
- 分かったこと：会話・議事録から構成・画面・データ・外部連携と採用理由を説明する。事実・設計案・未決事項を区別する。複数の図で理解をそろえ、冗長な説明と独自略語を避ける。13件の成功・失敗の判定と4つの検証題材を利用者が確認した。
- 出典：[Issue #102](https://github.com/yukihito-jokyu/context/issues/102)、[評価と対話](eval/eval.json)。
- 使ったルール：IN-01、IN-02、STEP-02、OUT-02、OUT-03、OUT-04、OUT-08、OUT-09

## 流用元の生成と検査

- 確認方法：write-requirement-document/SKILL.md、scripts/document.py、dev/spec.json、references/authoring.mdを確認（2026-11-04）。
- 確認の状態：確認済み
- 分かったこと：JSON原本からMermaid・PNG・HTML・manifestを生成し、参照・PNGの署名とCRC・寸法・SHA-256・HTMLの再生成一致を検査する。図の前後に導入と要点を置き、内部IDを本文へ出さない。基本設計では要望と設計判断を別の配列にし、設計の根拠と採用理由、詳細設計への引継ぎを追加する。
- 出典：[流用元の実装](../../write-requirement-document/scripts/document.py)、[流用元の手順](../../write-requirement-document/SKILL.md)。
- 使ったルール：STEP-01、STEP-03、STEP-05、OUT-01、OUT-05、OUT-06、OUT-07

## Mermaid CLI 11.16.0

- 確認方法：既存document.py doctor、既存mermaid-cliの--help、公式READMEを確認（2026-11-04）。Python 3.9以上とNode.jsが利用でき、mermaid-cli 11.16.0が既存の経路にあることを確認。
- 確認の状態：確認済み
- 分かったこと：CLIは入力と出力に-i/-o、設定に-c、Puppeteer設定に-p、背景色に-b、倍率に-sを受け取る。PNGへのローカル変換ができる。doctorで分かるのは経路と版であり、実描画はbuildで別途確かめる。標準ライブラリと既存のパッケージを使い、取得や更新は自動で行わない。
- 出典：[Mermaid CLI公式README](https://github.com/mermaid-js/mermaid-cli)。
- 使ったルール：STEP-04

## Mermaidの図の構文

- 確認方法：公式のデータ関係図・シーケンス図の説明を取得（2026-11-04）。公式サイトは12.3.0、ローカルCLIは11.16.0である。
- 確認の状態：確認済み
- 分かったこと：データの概念・論理関係はerDiagramまたはclassDiagramで表せる。シーケンス図はsequenceDiagramで相互作用と順序を表せる。ローカルの11以降で使えるflowchart、stateDiagram-v2、sequenceDiagram、classDiagram、erDiagramに限定し、新版固有の構文を前提にしない。
- 出典：[データ関係図の公式説明](https://mermaid.js.org/syntax/entityRelationshipDiagram.html)、[シーケンス図の公式説明](https://mermaid.js.org/syntax/sequenceDiagram.html)。
- 使ったルール：STEP-04、OUT-09

## HTMLの図と本文

- 確認方法：HTML Standardのfigure・figcaptionを確認（2026-11-04）。
- 確認の状態：確認済み
- 分かったこと：figureは本文から参照できる一組の図と説明を表し、figcaptionで説明を付けられる。検索できる本文、画像の代替説明、原寸表示、根拠への内部リンクを流用元から引き継ぐ。
- 出典：[HTML Standardのfigure](https://html.spec.whatwg.org/multipage/grouping-content.html#the-figure-element)。
- 使ったルール：OUT-02

## 共通正本の配置

- 確認方法：AGENTS.md、docs/skills/authoring/index.md、skill-foundation/references/platforms.mdを確認（2026-11-04）。
- 確認の状態：確認済み
- 決まり：AGENTS.mdの管理方針。「共通Skillの追加・更新では、該当する公開成果物を全削除し、更新後のSkillをサブエージェントで実行して再作成します。」
- 分かったこと：正本はutils/skills/documentation/へ置く。対象製品の入口はinstall.pyで正本へのリンクにする。共通Skillの利用ガイドと実行成果物を整備する。hooksの同梱はplugin配布として案内し、無関係なpluginを新設・導入しない。
- 出典：[管理方針](../../../../../AGENTS.md)、[共通スキルの配置](../../../../../docs/skills/authoring/index.md)。
- 使ったルール：OUT-01
