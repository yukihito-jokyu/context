# 評価JSON形式

AIは差分評価を次のJSON形式で`review-raw.json`へ直接保存する。説明文やMarkdownフェンスを混ぜず、実行固有のJSON生成スクリプトを作らない。構造とdiffとの対応は`validate_review.py`で検証する。

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
    },
    {
      "verdict": "rule_gap",
      "rule_ids": [],
      "locations": [
        {
          "file": "src/user-controller.ts",
          "side": "new",
          "lines": [31, 32]
        }
      ],
      "reason": "失敗時の再試行回数を3回に固定しているが、指定ルールに回数の根拠がない。",
      "suggestion": "外部サービス失敗時の最大再試行回数と、再試行しない失敗分類を定める。",
      "confidence": "medium"
    }
  ]
}
```

## 値の制約

- `verdict`: `rule_in`、`rule_out`、`unknown`、`no_rule`、`rule_gap`
- `side`: 追加・変更後の行は`new`、削除行は`old`
- `confidence`: `high`、`medium`、`low`
- `rule_in`と`rule_out`には少なくとも1件の`rule_ids`を指定する。
- `no_rule`の`rule_ids`は空配列にする。
- `rule_gap`の`rule_ids`は空配列にし、`reason`へ不足している判断、`suggestion`へ検討用の提案ルールを空でない文字列として記録する。
- `locations[].lines`には差分JSONに存在する変更行だけを昇順で指定する。
- すべての追加行と削除行を、少なくとも1件の`rule_gap`以外の通常評価で覆う。`rule_gap`だけでは行網羅を満たさない。
- 一つの根拠が連続する複数行へ適用される場合は、一つのlocationへまとめる。
- 一つの評価は一つの`verdict`だけを持つ。同じ変更行を通常評価と`rule_gap`が参照する場合も、別reviewとして記録する。
- `rule_gap`は未承認の提案であり、承認済みルールや自動修正指示として扱わない。
- ルールが競合する場合や依頼内容が不足する場合は、推測せず`unknown`にする。

`validate_review.py`が安定した`review_id`と`line_range`を付与するため、AIはこれらを生成しない。
