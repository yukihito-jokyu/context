# generate-domain-model の調査

## 要件と対象範囲

- 確認方法：Issue #87の本文と承認済み計画 https://github.com/yukihito-jokyu/context/issues/87#issuecomment-6420005520 （2026-10-27）
- 確認の状態：確認済み
- 分かったこと：実コードの根拠付きモデル情報、Mermaid、PNG、HTMLカタログを作る。全言語の完全AST抽出は対象外。
- 使った決定：IN-01、IN-02、STEP-01、OUT-01、OUT-02、OUT-03

## Mermaid CLI 11.16.0 と classDiagram

- 確認方法：既存のmmdc --version → 11.16.0、--help → -i/-o/-p/-b/-sを確認（2026-10-27）。https://github.com/mermaid-js/mermaid-cli#usage と https://mermaid.js.org/syntax/classDiagram.html を取得して確認。
- 確認の状態：確認済み
- 分かったこと：classDiagramはクラス表示名、属性、関係と多重度を表せる。Mermaid CLIは拡張子pngでPNGを生成する。CLIを同梱・自動ダウンロードせず、インストール済みのCLIを明示して使う。sandbox内のChrome起動は失敗したため、同じCLIを実行権限のある隔離作業場所で実行すると終了コード0でPNGを生成でき、日本語・多重度・関係名を目視確認した。
- 使った決定：STEP-04、OUT-02

## 共通ランタイム

- 確認方法：skill-foundationのreferences/runtime.mdとreferences/platforms.md、生成された4つのランタイムを確認（2026-10-27）。
- 確認の状態：確認済み
- 分かったこと：start/check/finish、契約のcommand検査、hooksの製品別入出力は既存ランタイムをそのまま使う。出力は実行記録配下に作り、対象コードを変更しない。
- 使った決定：OUT-01
