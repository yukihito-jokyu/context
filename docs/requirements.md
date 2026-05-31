# Context Repository 要件定義

## 1. 概要

本リポジトリは、Claude Code・CodexなどのAI Agent向けコンテキストを一元管理するためのリポジトリである。

各開発リポジトリに個別管理されている以下のようなコンテキストを集約し、再利用性と保守性を向上させることを目的とする。

- AGENTS.md
- CLAUDE.md
- Skill（SKILL.md）

また、本リポジトリ自体もAI Agentによって管理されることを前提とする。

---

# 2. 設計方針

## 2.1 コンテキストの正本管理

各開発リポジトリは正本を持たない。

すべてのコンテキストは Context Repository に集約する。

配布先リポジトリには生成物・コピーを配置する。

---

## 2.2 プロジェクト単位管理

コンテキストは Git リポジトリ単位で管理する。

```text
projects/<repo-name>/
```

を1つの管理単位とする。

---

## 2.3 共通Skill管理

複数プロジェクトで利用可能なSkillは

```text
utils/skills/
```

に配置する。

---

## 2.4 プロジェクト固有Skill管理

プロジェクト固有Skillは

```text
projects/<repo-name>/skills/
```

に配置する。

---

# 3. フォルダ構成

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

# 4. ドキュメント責務

## 4.1 SKILL.md

Skillの正本。

### 責務

- Skillの目的
- Skillのルール
- Skillのワークフロー

### テンプレート

```md
# Skill Name

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

## 4.2 README.md

Skillカタログ。

正本ではない。

SKILL.mdの内容を要約して生成・更新する。

### 記載内容

- Skill名
- 目的
- 使うタイミング
- 使い方

### 正本関係

```text
SKILL.md
  ↓
README.md
```

矛盾時は SKILL.md を正とする。

---

## 4.3 AGENTS.md

リポジトリ方針の正本。

### 記載内容

- プロジェクト概要
- アーキテクチャ概要
- コーディング規約
- 利用すべきSkill
- 作業時の注意事項

具体的な手順は記載しない。

手順はSkillへ切り出す。

---

# 5. projects/context

## 目的

Context Repository 自身を管理するためのプロジェクト。

### 例

```text
projects/context/
```

### 配置Skill例

- skill-authoring
- readme-authoring
- agents-authoring

---

## AGENTS正本

```text
projects/context/AGENTS.md
```

を正本とする。

---

## 配布

```bash
context deploy context
```

により

```text
context/AGENTS.md
```

へ配布する。

---

# 6. Skill Authoring

## 目的

Skill作成・更新・レビューを支援する管理Skill。

---

## 実行フロー

### Step0

ユーザーへ確認

- Skill作成用プロンプトが存在するか
- 既存Skillとして配置済みか
- 配置済みなら配置場所はどこか

---

### Step1

既存Skill調査

調査対象

```text
utils/skills/*
projects/*/skills/*
```

---

### Step2

重複判定

以下を考慮する。

- Skill名
- 目的
- 適用範囲
- ワークフロー

---

### Step3

提案

- 既存Skill拡張
- Skill統合
- 新規Skill作成

を提案する。

---

### Step4

SKILL.md生成

---

### Step5

README更新案生成

---

### Step6

レビュー観点提示

---

# 7. CLI

実装言語

```text
Go
```

---

## コマンド名

```bash
context
```

---

## 主コマンド

```bash
context deploy
context deploy <repo-name>
```

---

# 8. Deploy

## 配布先

コマンド実行時のカレントディレクトリ。

例

```bash
cd ~/workspace/my-repo

context deploy spring-boot-api
```

---

## 配布候補Skill

```text
projects/<repo>/skills/*
utils/skills/*
```

---

## 優先順位

同名Skillが存在する場合

```text
projects/<repo>/skills
```

を優先する。

---

## Skill選択

ユーザーが対話的に選択する。

保存は行わない。

毎回選択する。

---

## AGENTS.md

配布有無をユーザーが選択する。

---

## CLAUDE.md

生成有無をユーザーが選択する。

---

## README

配布しない。

---

# 9. 上書きルール

## Skill

既存Skillが存在する場合

```text
.claude/skills/<skill-name>
.codex/skills/<skill-name>
```

について確認する。

---

### 上書き許可

既存ディレクトリ削除

↓

新規コピー

---

## AGENTS.md

既存ファイルが存在する場合

ユーザーへ確認する。

---

## CLAUDE.md

既存ファイルが存在する場合

ユーザーへ確認する。

---

# 10. README運用

## utils/README.md

対象

```text
utils/skills/*
```

Skill追加・削除・名称変更時に更新する。

---

## projects/<repo>/README.md

対象

```text
projects/<repo>/skills/*
```

Skill追加・削除・名称変更時に更新する。

---

更新はAI Agentに依頼する。

人間は内容を微修正可能とする。

ただしフォーマットは維持する。

---

# 11. 非機能要件

## AI Agent利用前提

本リポジトリはAI Agentとの共同管理を前提とする。

---

## 単一正本

同じ情報を複数箇所で管理しない。

---

## Skill中心設計

コンテキストの中心はSkillとする。

ノウハウ・運用手順・レビュー手順はSkillとして管理する。

---

## シンプルな構造

不要なカテゴリ階層は導入しない。

```text
projects/
```

はフラット構成とする。
