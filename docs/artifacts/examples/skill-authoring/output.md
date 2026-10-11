# 配置先の判断結果

入力: 「提供する成果物リンク確認のプロンプトを、隔離したサンプル作業領域で共通スキルにし、カタログを整備する。contextの正本は変更しない。」

## 調査した正本とカタログ

utils/skills/README.md、docs/authoring/index.md、skill-authoring、my-skill-creator、agent-trace、issue-traceのSKILL.mdを読んだ。

## 既存スキルを更新するか

既存の証跡記録とスキル作成の責務は分かれている。サンプルでは提供したプロンプトの範囲を成果物リンク検査に限定し、新規SKILL.mdを作成した。contextの既存スキルの動作は変更していない。

## 配置判断

- 検査内容はDocusaurusの設定に限定されず、複数プロジェクトの成果物展示に再利用できるため共通スキルと判定した。
- サンプル領域のutils/skills/documentation/artifact-links/SKILL.mdへ配置した。
- 分類は1階層。サンプル領域に同名スキルが存在しないことを確認して新規作成した。

## 実施範囲

SKILL.mdとutils/skills/README.mdを実際に作成した。READMEは目的の要約と正本へのリンクに限定した。本文プロンプトを入力に含めたためgrill-skillは起動していない。実ファイルはZIPへ保存する。

## 保留事項

このスキルを実運用へ採用するかは別の判断。サンプル生成からcontextの正本への導入許可を推測しない。
