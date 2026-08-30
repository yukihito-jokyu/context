# 評価JSON形式

AIは差分評価を次のJSON形式で保存する。説明文やMarkdownフェンスを混ぜない。

```json
{
  "schema_version": "1.0",
  "rules": [
    {
      "rule_id": "project-input-validation",
      "skill": "project-rules",
      "source": "/absolute/path/rules.md",
      "heading": "入力値検証",
      "text": "外部入力はサービスへ渡す前に検証する。"
    }
  ],
  "reviews": [
    {
      "verdict": "rule_out",
      "rule_ids": ["project-input-validation"],
      "locations": [
        {
          "file": "src/user-controller.ts",
          "side": "new",
          "lines": [23, 24, 25, 26, 27]
        }
      ],
      "reason": "入力値を検証せずサービスへ渡している。",
      "suggestion": "サービス呼び出し前に形式を検証する。",
      "confidence": "high"
    }
  ]
}
```

## 値の制約

- `verdict`: `rule_in`、`rule_out`、`unknown`、`no_rule`
- `side`: 追加・変更後の行は`new`、削除行は`old`
- `confidence`: `high`、`medium`、`low`
- `rule_in`と`rule_out`には少なくとも1件の`rule_ids`を指定する。
- `no_rule`の`rule_ids`は空配列にする。
- `locations[].lines`には差分JSONに存在する変更行だけを昇順で指定する。
- すべての追加行と削除行を、少なくとも1件の評価で覆う。
- 一つの根拠が連続する複数行へ適用される場合は、一つのlocationへまとめる。
- ルールが競合する場合や依頼内容が不足する場合は、推測せず`unknown`にする。

`validate_review.py`が安定した`review_id`と`line_range`を付与するため、AIはこれらを生成しない。
