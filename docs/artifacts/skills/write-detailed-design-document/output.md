## 結果

write-detailed-design-document: 完了（検証に合格）

## 詳細設計書

- [入口文書](/private/tmp/detailed-design-public-nu7gtxsu/deliverables/reservation-design/README.md)
- 機能 4 件、要件 5 件、確認条件 14 件
- 図 70 件をMermaidとPNGで保存している。
- 未決 3 件、要件変更 0 件
- 文書検査の通過と、採用判断・実装・実機検証の結果は別に記録している。

## 出力

- `deliverables/reservation-design/design.json`（design-data 設計の台帳）
- `deliverables/reservation-design/README.md`（entry 入口文書）
- `deliverables/reservation-design/common.md`（common-design 共通仕様）
- `deliverables/reservation-design/features.md`（feature-design 機能詳細）
- `deliverables/reservation-design/interfaces.md`（interface-design 境界の契約）
- `deliverables/reservation-design/data.md`（data-design 物理データ）
- `deliverables/reservation-design/ui.md`（ui-design 画面）
- `deliverables/reservation-design/recovery.md`（recovery-design 障害と再起動）
- `deliverables/reservation-design/verification.md`（verification-design 対応と確認条件）
- `deliverables/reservation-design/evidence.md`（evidence-design 根拠と未決と変更）
- `deliverables/reservation-design/review.html`（review-view 分野別の閲覧と確認）
- `deliverables/reservation-design/diagrams/manifest.json`（diagram-assets 図の原本と画像の対応）

## 既定値で決めた値

- なし

## 入力で読めなかった値

- なし

## 検証

- `run.py finish`: 指摘 0 件

## 補足

- 本書は未承認の設計案である。実装・実DB・外部サービス接続・負荷・移行の試験と設計採用の承認は未実施であり、U001〜U003に採用条件と影響を記録した。
- 全70図を18枚の一覧で実画像確認し、35図を元PNGでも拡大確認した。12分野全25ページの意味照合と確認範囲はdeliverables/reservation-design/verification-review.mdに記録した。
- PostgreSQL対象版・認証方式、上限値・監視間隔・受付結果の保管方針は採用前に確認する。追加取得・外部通信・導入・hooks登録・外部投稿・コミット・pushは行っていない。
