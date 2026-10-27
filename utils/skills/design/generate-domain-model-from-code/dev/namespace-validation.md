# 同名追加の衝突解消

mainに入ったPR #92は、Issue #86の資料・Mermaidから図を作る `generate-domain-model` を追加している。Issue #87の本Skillはコードの行・抜粋・ハッシュを辿れるモデルを作るため、既存実装を維持し、本Skillとpluginを `generate-domain-model-from-code` へ改名した。判断基準・モデル形式・ランタイムの制御は変更していない。

改名後の確認：

- 基準カタログを既存Mermaid CLI 11.16.0とChromeで実際に再生成し、3図・3概念・2関係の検査が成功。
- `probe.py`：違反例21件、hooks配線20件が成功。`results/probe-results.json` が現行名の結果。
- `python3 -m unittest discover -s utils/skills/design/generate-domain-model-from-code/dev -p test_catalog.py`：12件成功。

公開サンプルとplugin配布物は、封印後の正本を新しいサブエージェントが実行して作り直す。実行結果と正本・成果物のSHA-256は `docs/artifacts/skills/generate-domain-model-from-code/execution.json` と `docs/artifacts/plugins/generate-domain-model-from-code/execution.json` に記録する。

`results/convergence/` は改名前に行った3ラウンドの原本であり、書き換えていない。汎用収束指標の残差とClaude API制限による未確認範囲も、従来の収束記録に残している。
