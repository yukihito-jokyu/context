入力データは `utils/skills/development/llm-eval/assets/example-review-data.json` の同梱サンプルです。同じ内容を `review-data.json` として保存しています。問い合わせ分類の架空の2ケースを含み、評価実行結果は空です。

スキルのディレクトリから次のコマンドを実行しました。

python3 scripts/build_review.py --data assets/example-review-data.json --output ../../../../docs/artifacts/examples/llm-eval/review.html

これは配置後のHTML生成確認です。モデル評価や、人間が合意した基準による評価実行は含みません。
