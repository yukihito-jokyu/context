# generate-domain-model の調査

## 要件と業務図の粒度

- 確認方法：2026-10-27、[Issue #86の承認済み計画](https://github.com/yukihito-jokyu/context/issues/86#issuecomment-6419993821)と会話の回答「業務の概念と関係を表す」を確認した。
- 確認の状態：確認済み
- 分かったこと：Mermaid原本、PNG、HTMLカタログを生成し、資料にない多重度を断定しない。
- 使った決定：IN-01、IN-02、OUT-01、OUT-02、OUT-03

## Mermaid CLI 12.0.0

- 確認方法：2026-10-27、mmdc --version → 12.0.0、mmdc --help を実行し、[公式CLI](https://github.com/mermaid-js/mermaid-cli/tree/12.0.0)と[クラス図仕様](https://mermaid.js.org/syntax/classDiagram.html)を確認した。
- 確認の状態：確認済み
- 分かったこと：-i はMermaid原本、-o はPNG、-c はMermaid設定、-p はブラウザ設定、-s は描画倍率である。classDiagram は概念、属性、関連と多重度を表現できる。導入版を固定し、引数はシェルを介さず配列で渡す。
- 使った決定：STEP-02

## 検査と共通ランタイム

- 確認方法：2026-10-27、skill-foundation の references/runtime.md、references/platforms.md と生成された scripts/run.py の cmd_check・cmd_finish を読んだ。
- 確認の状態：確認済み
- 分かったこと：出力の件数は変更されたファイルを数える。全出力はreport.sectionsでも検査するため、変更がない更新でも欠落を見逃さない。共通ランタイムの出力検査はUTF-8テキスト専用で、PNGを直接outputsに登録すると失敗した。PNGは限定したallow_changesで置き場を許可し、catalog.pyのcommand検査とreport.sectionsで必須件数・画像形式・ハッシュを検査する。共通ランタイム自体は変更しない。hooksは両Agent向けに生成される。生成する固有Pythonスクリプトは標準ライブラリだけで動く。
- 使った決定：OUT-07、STEP-04

## 独立実行で確認した環境と差

- 確認方法：2026-10-27、dev/results/environment-pilot.json の独立したClaude Code・Codexの実行を確認した。
- 確認の状態：確認済み
- 分かったこと：Claude CodeはPNG生成とfinishまで完了した。Codexのworkspace-writeではChrome起動が拒否されabortした。評価用runner_commandsのCodexだけをdanger-full-accessに変更し、使い捨て評価プロジェクトで再実行し、PNG生成からfinishまで完了した。入力を読む範囲と出力先は各プロンプトで限定し、実利用プロジェクトの設定は変えない。引用の分割数とtermsの選択に差があり、同じファイルの引用の集約とMermaidの概念からのterms生成をスクリプトに移した。
- 使った決定：OUT-04

## 収束測定で固定した参照パスと再生成

- 確認方法：2026-10-27、dev/results/convergence/round-1〜4/report.json と dev/test_catalog.py を確認した。
- 確認の状態：確認済み
- 分かったこと：同じ原本でもPNGを再生成すると変更の有無に差が出たため、原本・変換版・設定・画像ハッシュが一致する画像を保持する。根拠パスに評価セッションの絶対パスが入る差は、プロジェクト内の参照を相対パスへ統一することで解消した。4課題のファイル・構造・名前の一致度はラウンド4で各1.000になった。Claude Codeはラウンド2途中から利用先APIの利用量上限で実行できなくなり、以後の測定はCodexで行った。
- 使った決定：OUT-04、OUT-06、STEP-04
