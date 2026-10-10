# JSONスキーマ

この文書は skill-creator で使用するJSONスキーマを定義します。

---

## evals.json

スキルの評価を定義します。スキルディレクトリ内の `evals/evals.json` に配置します。

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "ユーザーのプロンプト例",
      "expected_output": "期待される結果の説明",
      "files": ["evals/files/sample1.pdf"],
      "expectations": [
        "出力にXが含まれる",
        "スキルがスクリプトYを使用した"
      ]
    }
  ]
}
```

**フィールド:**
- `skill_name`: スキルのフロントマターの名前と一致する名前
- `evals[].id`: 一意の整数識別子
- `evals[].prompt`: 実行するタスク
- `evals[].expected_output`: 人間が読める成功条件の説明
- `evals[].files`: 入力ファイルパスの任意リスト（スキルルートからの相対パス）
- `evals[].expectations`: 検証可能な記述のリスト

---

## history.json

改善モードにおけるバージョンの推移を追跡します。ワークスペースのルートに配置します。

```json
{
  "started_at": "2026-01-15T10:30:00Z",
  "skill_name": "pdf",
  "current_best": "v2",
  "iterations": [
    {
      "version": "v0",
      "parent": null,
      "expectation_pass_rate": 0.65,
      "grading_result": "baseline",
      "is_current_best": false
    },
    {
      "version": "v1",
      "parent": "v0",
      "expectation_pass_rate": 0.75,
      "grading_result": "won",
      "is_current_best": false
    },
    {
      "version": "v2",
      "parent": "v1",
      "expectation_pass_rate": 0.85,
      "grading_result": "won",
      "is_current_best": true
    }
  ]
}
```

**フィールド:**
- `started_at`: 改善を開始した時刻のISOタイムスタンプ
- `skill_name`: 改善対象のスキル名
- `current_best`: 最も優れたバージョンの識別子
- `iterations[].version`: バージョン識別子（v0、v1、...）
- `iterations[].parent`: このバージョンの元となった親バージョン
- `iterations[].expectation_pass_rate`: 採点による成功率
- `iterations[].grading_result`: "baseline"、"won"、"lost"、または "tie"
- `iterations[].is_current_best`: 現在の最良バージョンかどうか

---

## grading.json

採点エージェントの出力です。`<run-dir>/grading.json` にあります。

```json
{
  "expectations": [
    {
      "text": "出力に『John Smith』という名前が含まれる",
      "passed": true,
      "evidence": "トランスクリプトのステップ3で発見: 『抽出した名前: John Smith、Sarah Johnson』"
    },
    {
      "text": "スプレッドシートのセルB10にSUM数式がある",
      "passed": false,
      "evidence": "スプレッドシートは作成されなかった。出力はテキストファイルだった。"
    }
  ],
  "summary": {
    "passed": 2,
    "failed": 1,
    "total": 3,
    "pass_rate": 0.67
  },
  "execution_metrics": {
    "tool_calls": {
      "Read": 5,
      "Write": 2,
      "Bash": 8
    },
    "total_tool_calls": 15,
    "total_steps": 6,
    "errors_encountered": 0,
    "output_chars": 12450,
    "transcript_chars": 3200
  },
  "timing": {
    "executor_duration_seconds": 165.0,
    "grader_duration_seconds": 26.0,
    "total_duration_seconds": 191.0
  },
  "claims": [
    {
      "claim": "フォームには入力可能なフィールドが12個ある",
      "type": "factual",
      "verified": true,
      "evidence": "field_info.json で12個のフィールドを数えた"
    }
  ],
  "user_notes_summary": {
    "uncertainties": ["2023年のデータを使用したため、古い可能性がある"],
    "needs_review": [],
    "workarounds": ["入力できないフィールドにはテキストのオーバーレイを使用した"]
  },
  "eval_feedback": {
    "suggestions": [
      {
        "assertion": "出力に『John Smith』という名前が含まれる",
        "reason": "名前に言及しただけの幻覚的な文書でも成功してしまう"
      }
    ],
    "overall": "アサーションは存在を確認するだけで、正しさを確認していない。"
  }
}
```

**フィールド:**
- `expectations[]`: 根拠を含む採点済み期待値
- `summary`: 成功・失敗数の集計
- `execution_metrics`: ツール使用状況と出力サイズ（実行者のmetrics.jsonから）
- `timing`: 実時間（timing.jsonから）
- `claims`: 出力から抽出・検証された主張
- `user_notes_summary`: 実行者が指摘した問題
- `eval_feedback`: （任意）評価に対する改善案。採点者が提起に値する問題を特定した場合のみ存在する

---

## metrics.json

実行エージェントの出力です。`<run-dir>/outputs/metrics.json` にあります。

```json
{
  "tool_calls": {
    "Read": 5,
    "Write": 2,
    "Bash": 8,
    "Edit": 1,
    "Glob": 2,
    "Grep": 0
  },
  "total_tool_calls": 18,
  "total_steps": 6,
  "files_created": ["filled_form.pdf", "field_values.json"],
  "errors_encountered": 0,
  "output_chars": 12450,
  "transcript_chars": 3200
}
```

**フィールド:**
- `tool_calls`: ツール種別ごとの回数
- `total_tool_calls`: すべてのツール呼び出しの合計
- `total_steps`: 主な実行手順の数
- `files_created`: 作成された出力ファイルのリスト
- `errors_encountered`: 実行中のエラー数
- `output_chars`: 出力ファイルの総文字数
- `transcript_chars`: トランスクリプトの文字数

---

## timing.json

実行の実時間です。`<run-dir>/timing.json` にあります。

**取得方法:** サブエージェントタスクが完了すると、タスク通知には `total_tokens` と `duration_ms` が含まれます。これらは直ちに保存してください。他には永続化されず、後から復元できません。

```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3,
  "executor_start": "2026-01-15T10:30:00Z",
  "executor_end": "2026-01-15T10:32:45Z",
  "executor_duration_seconds": 165.0,
  "grader_start": "2026-01-15T10:32:46Z",
  "grader_end": "2026-01-15T10:33:12Z",
  "grader_duration_seconds": 26.0
}
```

---

## benchmark.json

ベンチマークモードの出力です。`benchmarks/<timestamp>/benchmark.json` にあります。

```json
{
  "metadata": {
    "skill_name": "pdf",
    "skill_path": "/path/to/pdf",
    "executor_model": "claude-sonnet-4-20250514",
    "analyzer_model": "most-capable-model",
    "timestamp": "2026-01-15T10:30:00Z",
    "evals_run": [1, 2, 3],
    "runs_per_configuration": 3
  },

  "runs": [
    {
      "eval_id": 1,
      "eval_name": "Ocean",
      "configuration": "with_skill",
      "run_number": 1,
      "result": {
        "pass_rate": 0.85,
        "passed": 6,
        "failed": 1,
        "total": 7,
        "time_seconds": 42.5,
        "tokens": 3800,
        "tool_calls": 18,
        "errors": 0
      },
      "expectations": [
        {"text": "...", "passed": true, "evidence": "..."}
      ],
      "notes": [
        "2023年のデータを使用したため、古い可能性がある",
        "入力できないフィールドにはテキストのオーバーレイを使用した"
      ]
    }
  ],

  "run_summary": {
    "with_skill": {
      "pass_rate": {"mean": 0.85, "stddev": 0.05, "min": 0.80, "max": 0.90},
      "time_seconds": {"mean": 45.0, "stddev": 12.0, "min": 32.0, "max": 58.0},
      "tokens": {"mean": 3800, "stddev": 400, "min": 3200, "max": 4100}
    },
    "without_skill": {
      "pass_rate": {"mean": 0.35, "stddev": 0.08, "min": 0.28, "max": 0.45},
      "time_seconds": {"mean": 32.0, "stddev": 8.0, "min": 24.0, "max": 42.0},
      "tokens": {"mean": 2100, "stddev": 300, "min": 1800, "max": 2500}
    },
    "delta": {
      "pass_rate": "+0.50",
      "time_seconds": "+13.0",
      "tokens": "+1700"
    }
  },

  "notes": [
    "『出力がPDFファイルである』というアサーションは両構成で100%成功しており、スキルの価値を区別できない可能性がある",
    "評価3は大きなばらつき（50% ± 40%）を示し、不安定またはモデル依存の可能性がある",
    "スキルなしの実行は、表抽出の期待値を一貫して満たせない",
    "スキルは平均実行時間を13秒増やすが、成功率を50%改善する"
  ]
}
```

**フィールド:**
- `metadata`: ベンチマーク実行に関する情報
  - `skill_name`: Name of the skill
  - `timestamp`: ベンチマークを実行した時刻
  - `evals_run`: 評価名またはIDのリスト
  - `runs_per_configuration`: 構成ごとの実行回数（例: 3）
- `runs[]`: 個別の実行結果
  - `eval_id`: 数値の評価識別子
  - `eval_name`: 人間が読める評価名（ビューアでは節見出しとして使われる）
  - `configuration`: `"with_skill"` または `"without_skill"` でなければならない（ビューアはグループ化と色分けにこの正確な文字列を使う）
  - `run_number`: 整数の実行番号（1、2、3…）
  - `result`: `pass_rate`、`passed`、`total`、`time_seconds`、`tokens`、`errors` を持つネストされたオブジェクト
- `run_summary`: 構成ごとの統計集計
  - `with_skill` / `without_skill`: それぞれに `mean` と `stddev` フィールドを持つ `pass_rate`、`time_seconds`、`tokens` オブジェクトを含む
  - `delta`: `"+0.50"`、`"+13.0"`、`"+1700"` のような差分文字列
- `notes`: 分析器による自由形式の観察

**重要:** ビューアはこれらのフィールド名を正確に読み取ります。`configuration` の代わりに `config` を使う、または `pass_rate` を `result` の下にネストせず実行の最上位に置くと、ビューアは空またはゼロの値を表示します。benchmark.jsonを手作業で生成する場合は、必ずこのスキーマを参照してください。

---

## comparison.json

盲検比較器の出力です。`<grading-dir>/comparison-N.json` にあります。

```json
{
  "winner": "A",
  "reasoning": "出力Aは適切な書式と必要なすべてのフィールドを備えた完全な解決策を提供している。出力Bには日付フィールドがなく、書式にも不整合がある。",
  "rubric": {
    "A": {
      "content": {
        "correctness": 5,
        "completeness": 5,
        "accuracy": 4
      },
      "structure": {
        "organization": 4,
        "formatting": 5,
        "usability": 4
      },
      "content_score": 4.7,
      "structure_score": 4.3,
      "overall_score": 9.0
    },
    "B": {
      "content": {
        "correctness": 3,
        "completeness": 2,
        "accuracy": 3
      },
      "structure": {
        "organization": 3,
        "formatting": 2,
        "usability": 3
      },
      "content_score": 2.7,
      "structure_score": 2.7,
      "overall_score": 5.4
    }
  },
  "output_quality": {
    "A": {
      "score": 9,
      "strengths": ["完全な解決策", "適切な書式", "すべてのフィールドがある"],
      "weaknesses": ["ヘッダーのスタイルに軽微な不整合がある"]
    },
    "B": {
      "score": 5,
      "strengths": ["読みやすい出力", "正しい基本構造"],
      "weaknesses": ["日付フィールドがない", "書式の不整合", "データ抽出が不完全"]
    }
  },
  "expectation_results": {
    "A": {
      "passed": 4,
      "total": 5,
      "pass_rate": 0.80,
      "details": [
        {"text": "出力に名前が含まれる", "passed": true}
      ]
    },
    "B": {
      "passed": 3,
      "total": 5,
      "pass_rate": 0.60,
      "details": [
        {"text": "出力に名前が含まれる", "passed": true}
      ]
    }
  }
}
```

---

## analysis.json

事後分析器の出力です。`<grading-dir>/analysis.json` にあります。

```json
{
  "comparison_summary": {
    "winner": "A",
    "winner_skill": "path/to/winner/skill",
    "loser_skill": "path/to/loser/skill",
    "comparator_reasoning": "比較器が勝者を選んだ理由の簡潔な要約"
  },
  "winner_strengths": [
    "複数ページの文書を扱うための明瞭な段階的指示",
    "書式エラーを検出した検証スクリプトを同梱している"
  ],
  "loser_weaknesses": [
    "『文書を適切に処理する』という曖昧な指示が一貫しない振る舞いにつながった",
    "検証スクリプトがなく、エージェントは即興で対応する必要があった"
  ],
  "instruction_following": {
    "winner": {
      "score": 9,
      "issues": ["軽微: 任意のログ記録手順を省略した"]
    },
    "loser": {
      "score": 6,
      "issues": [
        "スキルの書式テンプレートを使わなかった",
        "手順3に従わず独自の方法を考案した"
      ]
    }
  },
  "improvement_suggestions": [
    {
      "priority": "high",
      "category": "instructions",
      "suggestion": "『文書を適切に処理する』を明示的な手順へ置き換える",
      "expected_impact": "一貫しない振る舞いを招いた曖昧さを解消できる"
    }
  ],
  "transcript_insights": {
    "winner_execution_pattern": "スキルを読む → 5段階の手順に従う → 検証スクリプトを使う",
    "loser_execution_pattern": "スキルを読む → 方法が不明瞭 → 3つの異なる方法を試す"
  }
}
```
