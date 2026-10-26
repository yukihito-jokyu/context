# Claude Code と Codex の違い

作ったスキルは、Claude Code と Codex のどちらでも同じ手順で動く。そのために、製品ごとの違いはスクリプトの側で吸収し、SKILL.md と契約は1つにする。この章では、吸収している違いと、作る人が知っておく違いを挙げる。

この章は次の順に読む。1章でスキルの置き場と読まれ方を、2章で hooks を、3章で収束テストに使う起動方法を確かめる。調べた日付と出典は skill-foundation の `dev/research.md` にある。

## 1. スキルの置き場と読まれ方

| 項目 | Claude Code | Codex |
|---|---|---|
| プロジェクトの置き場 | `.claude/skills/<name>/SKILL.md` | `.agents/skills/<name>/SKILL.md`（作業ディレクトリからリポジトリのルートまで探す） |
| シンボリックリンク | 辿る | 辿る |
| frontmatter で読むキー | `name`、`description` ほか。未知のキーは無視する | `name`、`description` |
| description の上限 | 一覧で 1536 文字に切り詰める | 一覧で 1024 文字に切り詰める |
| 自動起動を止める設定 | frontmatter の `disable-model-invocation: true` | 使わない |
| 明示の起動 | `/<name>` | `$<name>` |
| スキル内のパスの参照 | `${CLAUDE_SKILL_DIR}` が使える | 変数は無い |

skill-foundation はこの違いを次のように吸収する。

- frontmatter は `name` と `description` だけにし、自動起動を止めるときだけ `disable-model-invocation: true` を足す。description は 1024 文字以下にする（`skill_lint.py`）
- SKILL.md の中では、スキルのディレクトリを `<skill>`（SKILL.md があるディレクトリ）と書き、製品の変数を使わない
- 両方に対応するときは、本体を `.claude/skills/<name>` に置き、`.agents/skills/<name>` を相対シンボリックリンクにする（`install.py`）

## 2. hooks

hooks は、AI がファイルを編集した後、応答を終える前、保護ファイルを編集する前に、`scripts/hook.py` を実行する仕組みである。製品ごとの入力と出力の形の違いは、`hook.py --platform claude|codex` が吸収する。

| 項目 | Claude Code | Codex |
|---|---|---|
| 設定ファイル | `.claude/settings.json` | `.codex/hooks.json` |
| 使うイベント | PreToolUse、PostToolUse、Stop、UserPromptSubmit | 同じ |
| ファイル編集のツール | `Edit`、`Write`、`MultiEdit`、`NotebookEdit`（`tool_input.file_path`） | `apply_patch`（`tool_input.command` のパッチ本文の `*** Add File:`、`*** Update File:`、`*** Delete File:`、`*** Move to:` の行） |
| 編集の前に止める | `permissionDecision: "ask"`（ユーザーに確かめる） | `permissionDecision: "deny"`（ask が無い） |
| 実行していないときの、封印したスキルの編集 | `permissionDecision: "ask"`（ユーザーに確かめる） | 何もしない（deny にすると利用者の保守まで止まる。次の `run.py start` が封印との違いで止める） |
| 編集の後と終える前の差し戻し | `{"decision": "block", "reason": ...}` | 同じ。Stop の `reason` は新しいユーザーの指示として扱われる |
| Stop の出力 | JSON か空 | JSON でなければならない |
| 差し戻しの回数 | `hook.py` が `state.json` の `stop_blocks` で数える（製品の仕組みに頼らない） | 同じ |
| プロジェクトのルート | `$CLAUDE_PROJECT_DIR` | 変数が無いので `git rev-parse --show-toplevel` か `pwd` を使う |
| 実行の条件 | 設定を読めば実行する | `/hooks` で利用者が信頼するまで実行しない。プロジェクト自体が未信頼だと `.codex/` を読まない |

Codex の信頼は、hooks の宣言（コマンドの文字列）から計算する。呼び出すスクリプトの中身を変えても信頼は外れない。`install.py` は宣言を毎回同じ文字列で書くので、一度信頼すればスキルを作り直しても信頼し直す必要は無い。

`install.py` は既存の設定を残し、このスキルの項目だけを足す。同じ項目が既にあれば何もしない。`--uninstall` で自分の項目だけを外す。

## 3. 収束テストの起動方法

収束テストでは、作成に関わっていない独立エージェントを、会話の履歴を持たない状態で起動する。`convergence.py run` の既定のコマンドは次のとおりである。`{prompt}` と `{dir}` が置き換わる。spec の `convergence.runner_commands` で上書きできる。

| runner | コマンド | 理由 |
|---|---|---|
| `claude` | `claude -p {prompt} --output-format json --permission-mode acceptEdits --no-session-persistence --setting-sources project,local --allowedTools <一覧>` | ユーザー単位の設定（グローバルの指示と hooks）を読ませず、プロジェクトの設定だけで動かす |
| `codex` | `codex exec --json --sandbox workspace-write --skip-git-repo-check --ephemeral --dangerously-bypass-hook-trust -c projects."{dir}".trust_level="trusted" -C {dir} -o <最後の発言> {prompt}` | 一時プロジェクトの hooks は `/hooks` の信頼の手続きを経ていないため、このテストに限って信頼を飛ばす |
| `subagent` | 起動しない。`convergence.py prompts` が出したプロンプトを、呼び出し元の AI が Agent ツールで新しいエージェントに渡す | 上の2つを起動できない環境での代わり。hooks が働かないなどの制約は [convergence-test.md](convergence-test.md) の3章 |

- `codex` が PATH に無いときは、`$CODEX_HOME/packages/*/current/bin/codex` を探す。環境変数 `SKILL_FOUNDATION_CODEX` でパスを指定できる
- `codex exec` の既定のサンドボックスは読み取り専用なので、`--sandbox workspace-write` を付ける
- Claude Code の `--setting-sources project,local` は、ユーザーのグローバルの CLAUDE.md を読ませないためである。グローバルの指示がテストの結果に混ざると、スキルの効果を測れない
