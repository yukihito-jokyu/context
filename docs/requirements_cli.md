# Context CLI 要件定義

## 1. 概要

本ドキュメントは `docs/requirements.md` から CLI ツールに関する要件のみを抜き出したものである。

CLI ツールは、Context Repository で管理するコンテキストを各開発リポジトリへ配布するためのコマンドラインツールである。

---

## 2. 実装言語

```text
Go
```

---

## 3. コマンド名

```bash
context
```

---

## 4. 主コマンド

```bash
context deploy
context deploy <repo-name>
```

---

## 5. Deploy

### 5.1 配布先

配布先は、コマンド実行時のカレントディレクトリとする。

例:

```bash
cd ~/workspace/my-repo

context deploy spring-boot-api
```

### 5.2 projects/context の配布

`projects/context/AGENTS.md` は Context Repository 自身の `AGENTS.md` の正本である。

```bash
context deploy context
```

により、Context Repository ルートの `AGENTS.md` へ配布する。

---

## 6. 配布候補

### 6.1 Skill

配布候補 Skill は以下とする。

```text
projects/<repo>/skills/*
utils/skills/*
```

### 6.2 Skill の優先順位

同名 Skill が存在する場合は、以下を優先する。

```text
projects/<repo>/skills
```

### 6.3 Skill 選択

配布する Skill はユーザーが対話的に選択する。

選択結果は保存しない。

毎回選択する。

---

## 7. 配布対象ファイル

### 7.1 AGENTS.md

配布有無をユーザーが選択する。

### 7.2 CLAUDE.md

生成有無をユーザーが選択する。

### 7.3 README

README は配布しない。

---

## 8. 上書きルール

### 8.1 Skill

既存 Skill が存在する場合、以下についてユーザーに確認する。

```text
.claude/skills/<skill-name>
.codex/skills/<skill-name>
```

上書きが許可された場合は、既存ディレクトリを削除してから新規コピーする。

### 8.2 AGENTS.md

既存ファイルが存在する場合は、ユーザーへ確認する。

### 8.3 CLAUDE.md

既存ファイルが存在する場合は、ユーザーへ確認する。
