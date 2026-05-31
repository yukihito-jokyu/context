# Context Repository 詳細設計

## 1. ディレクトリ構成

```text
context/
├── README.md
├── AGENTS.md
├── CLAUDE.md
│
├── .claude/
│   └── skills/
│
├── .codex/
│   └── skills/
│
├── cli/
│   ├── go.mod
│   ├── main.go
│   ├── cmd/
│   │   ├── root.go
│   │   └── deploy.go
│   └── internal/
│       ├── project/
│       ├── skill/
│       ├── deploy/
│       ├── prompt/
│       └── filesystem/
│
├── utils/
│   ├── README.md
│   └── skills/
│       └── <skill-name>/
│           └── SKILL.md
│
└── projects/
    ├── context/
    │   ├── README.md
    │   ├── AGENTS.md
    │   └── skills/
    │       └── <skill-name>/
    │           └── SKILL.md
    │
    └── <repo-name>/
        ├── README.md
        ├── AGENTS.md
        └── skills/
            └── <skill-name>/
                └── SKILL.md
```

---

## 2. 主要概念

## 2.1 Project

`projects/<repo-name>/` を1つのProjectとする。

```go
type Project struct {
    Name       string
    Path       string
    AgentsPath string
    ReadmePath string
    SkillsDir  string
}
```

### ルール

- `projects/` 直下はフラット構成
- `<repo-name>` はディレクトリ名
- `README.md` は配布しない
- `AGENTS.md` は配布候補
- `skills/` はプロジェクト固有Skill候補

---

## 2.2 Skill

1つのSkillは1ディレクトリで表す。

```text
<skill-name>/
└── SKILL.md
```

```go
type Skill struct {
    Name   string
    Path   string
    Source SkillSource
}
```

```go
type SkillSource string

const (
    SkillSourceProject SkillSource = "project"
    SkillSourceUtils   SkillSource = "utils"
)
```

### ルール

- `SKILL.md` は必須
- `metadata.yaml` は持たない
- 同名Skillがある場合は Project 側を優先
- 配布時は選択されたSkillのみコピーする

---

## 2.3 DeployTarget

配布先はコマンド実行時のカレントディレクトリ。

```go
type DeployTarget struct {
    Root          string
    AgentsPath    string
    ClaudePath    string
    ClaudeSkills  string
    CodexSkills   string
}
```

### 配布先構造

```text
target-repo/
├── AGENTS.md
├── CLAUDE.md
├── .claude/
│   └── skills/
└── .codex/
    └── skills/
```

---

# 3. CLI設計

## 3.1 コマンド

```bash
context deploy
context deploy <repo-name>
```

---

## 3.2 `context deploy`

引数なしの場合、`projects/` 配下のProject一覧を表示し、ユーザーに選択させる。

```text
Select project:

> context
  spring-boot-api
  grasp-planning
```

---

## 3.3 `context deploy <repo-name>`

指定されたProjectを配布対象にする。

Projectが存在しない場合は類似候補を表示する。

```text
Project not found: spring

Did you mean?

> spring-boot-api
  spring-batch
```

---

# 4. Deploy処理フロー

```text
1. contextリポジトリルートを検出
2. Projectを決定
3. 配布先をカレントディレクトリに決定
4. Skill候補を収集
5. 同名Skillを解決
6. ユーザーにSkill選択させる
7. AGENTS.md配布有無を確認
8. CLAUDE.md生成有無を確認
9. 上書き確認
10. コピー実行
11. 結果表示
```

---

## 4.1 contextリポジトリルート検出

CLIは以下を満たすディレクトリをcontextリポジトリルートとみなす。

```text
projects/
utils/
cli/
```

優先順：

1. 環境変数 `CONTEXT_REPO`
2. 実行ファイルからの相対探索
3. カレントディレクトリから親方向探索

---

## 4.2 Project決定

### 引数あり

```bash
context deploy spring-boot-api
```

以下を確認する。

```text
projects/spring-boot-api/
```

存在すれば採用。

---

### 引数なし

`projects/` 直下のディレクトリを列挙し、選択させる。

---

## 4.3 配布先決定

```go
cwd, err := os.Getwd()
```

取得したカレントディレクトリを配布先とする。

可能であればGitリポジトリか確認する。

```bash
git rev-parse --show-toplevel
```

Gitリポジトリでない場合は警告を表示し、続行確認する。

---

# 5. Skill候補収集

## 5.1 収集対象

```text
projects/<repo>/skills/*
utils/skills/*
```

---

## 5.2 収集条件

Skillディレクトリとして扱う条件：

```text
<skill-name>/SKILL.md
```

が存在すること。

---

## 5.3 優先順位

同名Skillが存在する場合：

```text
projects/<repo>/skills/<skill-name>
```

を採用し、

```text
utils/skills/<skill-name>
```

は候補から除外する。

---

## 5.4 Skill候補モデル

```go
type SkillCandidate struct {
    Name        string
    Source      SkillSource
    SourcePath  string
    Description string
}
```

`Description` は初期実装では空でよい。

将来的に `SKILL.md` の冒頭から抽出して表示する。

---

# 6. 対話UI

GoのTUIライブラリは以下を候補とする。

- `github.com/charmbracelet/huh`
- `github.com/charmbracelet/bubbletea`

初期実装では `huh` を推奨する。

理由：

- チェックボックス選択が簡単
- 確認プロンプトが簡単
- 実装量が少ない

---

## 6.1 Skill選択

```text
Select skills to deploy:

[x] skill-authoring        project
[ ] git-workflow           utils
[x] spring-review          project
```

---

## 6.2 AGENTS.md確認

```text
Deploy AGENTS.md? [y/N]
```

---

## 6.3 CLAUDE.md確認

```text
Generate CLAUDE.md from AGENTS.md? [y/N]
```

CLAUDE.md の内容は AGENTS.md と同じ内容にする。

---

# 7. コピー仕様

## 7.1 Skillコピー先

選択されたSkillは両方へコピーする。

```text
.claude/skills/<skill-name>/
.codex/skills/<skill-name>/
```

---

## 7.2 コピー前作成

存在しなければ作成する。

```text
.claude/skills/
.codex/skills/
```

---

## 7.3 上書き判定

以下のどちらかが存在する場合、Skillは既存とみなす。

```text
.claude/skills/<skill-name>
.codex/skills/<skill-name>
```

---

## 7.4 Skill上書き

ユーザーが上書きを許可した場合：

```text
1. .claude/skills/<skill-name> を削除
2. .codex/skills/<skill-name> を削除
3. 新しいSkillを .claude/skills/<skill-name> にコピー
4. 新しいSkillを .codex/skills/<skill-name> にコピー
```

ユーザーが拒否した場合、そのSkillはスキップする。

---

## 7.5 AGENTS.mdコピー

配布元：

```text
projects/<repo>/AGENTS.md
```

配布先：

```text
AGENTS.md
```

既存ファイルがある場合は上書き確認する。

---

## 7.6 CLAUDE.md生成

入力：

```text
projects/<repo>/AGENTS.md
```

出力：

```text
CLAUDE.md
```

初期実装では内容をそのままコピーする。

既存ファイルがある場合は上書き確認する。

---

# 8. README運用設計

READMEはCLIでは配布しない。

READMEの生成・更新はAI Agentが行う。

---

## 8.1 utils/README.md

対象：

```text
utils/skills/*
```

目的：

共通Skillカタログ。

---

## 8.2 projects/<repo>/README.md

対象：

```text
projects/<repo>/skills/*
```

目的：

プロジェクト固有Skillカタログ。

---

## 8.3 READMEフォーマット

```md
# <repo-name> Context

## Skills

### <skill-name>

#### 目的

...

#### 使うタイミング

...

#### 使い方

...
```

---

# 9. SKILL.md設計

## 9.1 標準フォーマット

```md
# <Skill Name>

## 目的

...

## ルール

...

## ワークフロー

1. ...
2. ...
3. ...

## 出力形式（任意）

...
```

---

## 9.2 正本ルール

```text
SKILL.md = 正本
README.md = 要約
```

矛盾時は `SKILL.md` を正とする。

---

# 10. context自身の扱い

## 10.1 projects/context

`projects/context/` はcontextリポジトリ自身を管理するProject。

```text
projects/context/
├── README.md
├── AGENTS.md
└── skills/
```

---

## 10.2 context deploy context

以下を実行する。

```bash
cd /path/to/context
context deploy context
```

配布対象：

```text
projects/context/AGENTS.md -> context/AGENTS.md
projects/context/skills/*  -> context/.claude/skills/*
projects/context/skills/*  -> context/.codex/skills/*
```

`context/README.md` は配布対象外。

---

# 11. エラー設計

## 11.1 Project未検出

```text
Project not found: <name>
```

類似候補を表示する。

---

## 11.2 Skill未検出

```text
No skills found for project: <repo-name>
```

ただしAGENTS.mdのみ配布できるようにする。

---

## 11.3 AGENTS.md未検出

```text
AGENTS.md not found in projects/<repo-name>
```

AGENTS.md配布・CLAUDE.md生成はスキップする。

---

## 11.4 コピー失敗

```text
Failed to copy skill: <skill-name>
```

原因を表示する。

---

# 12. パッケージ設計

## 12.1 cmd

CLIエントリ。

```text
cmd/
├── root.go
└── deploy.go
```

---

## 12.2 internal/project

Project探索。

責務：

- Project一覧取得
- Project取得
- 類似Project候補取得

---

## 12.3 internal/skill

Skill探索・重複解決。

責務：

- utils Skill取得
- project Skill取得
- 同名Skill解決
- Skill候補生成

---

## 12.4 internal/deploy

配布処理。

責務：

- Skillコピー
- AGENTS.mdコピー
- CLAUDE.md生成
- 上書き確認との連携

---

## 12.5 internal/prompt

対話UI。

責務：

- Project選択
- Skill選択
- Yes/No確認

---

## 12.6 internal/filesystem

ファイル操作。

責務：

- ディレクトリコピー
- ファイルコピー
- 削除
- 存在確認

---

# 13. 初期実装スコープ

## MVP

```bash
context deploy
context deploy <repo-name>
```

対応内容：

- Project選択
- Skill選択
- Project優先のSkill解決
- `.claude/skills` へコピー
- `.codex/skills` へコピー
- AGENTS.md配布
- CLAUDE.md生成
- 上書き確認

---

## MVPではやらないこと

- README自動生成
- SKILL.md自動生成
- LLM API呼び出し
- metadata.yaml
- 配布履歴保存
- 選択状態保存
- docs/追加
- projects配下カテゴリ化

---

# 14. 将来拡張

```bash
context skill list
context skill validate
context readme check
context deploy --dry-run
context deploy --only claude
context deploy --only codex
```

---

# 15. 設計上の重要ルール

- CLIはLLM APIを呼ばない
- CLIはファイル管理に徹する
- Skill作成はAI Agentに任せる
- README更新はAI Agentに任せる
- READMEは配布しない
- Skillはユーザーが毎回選択する
- 選択状態は保存しない
- 上書きは必ず確認する
- 同名SkillはProject側を優先する
- `SKILL.md` がSkillの正本
- `projects/context` も通常Projectとして扱う
