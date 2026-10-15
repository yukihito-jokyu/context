# スキル構成の提案

今回の実成果物展示への依頼を入力として、繰り返す実例更新をスキル化するならどの構成が必要か検討した。my-skill-creatorの簡易モードの初回出力。構成確認前のため候補スキルの作成・評価は実行していない。

## 目的

実行した依頼と得られた成果物を保存し、Markdownの説明ページへ画像と原本取得を反映する。

## スキル本体の構成案

```text
artifact-examples/
├── SKILL.md
├── references/
│   └── artifact-formats.md
└── scripts/
    └── verify-artifacts.mjs
```

## 生成成果物の構成案

```text
artifact-examples-workspace/
├── skill-snapshot/
├── candidate-skill/iteration-1/
├── evals/
└── iteration-1/
    └── examples/<skill-name>/
        ├── input.md
        ├── execution.json
        └── 実出力・画面画像・ZIP
```

保存先はプロジェクトルートのartifact-examples-workspaceを提案する。これは提案のtreeであり、このスキルを作成した結果ではない。

## 既存スキルとの関係

skill-authoringは配置とカタログ整備を扱う。agent-traceは証跡を扱う。my-skill-creatorは候補作成と評価を扱うため、新規スキルが必要かは既存の役割を確認してから決める。

## 重要な未確定事項

- 新規スキルにするか、既存スキルの参照資料として扱うか。
- 出力形式と検証をどこまで自動化するか。
- 構成と保存先の合意。

今回の依頼はdocsの実例修正なので、正本スキルを新規作成・変更する承認には広げていない。
