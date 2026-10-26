# skill-foundation の調査

skill-foundation とそれが作るスキルが前提にする、Claude Code と Codex の仕様を出典付きで記録する。確かめた日はすべて 2026-10-26、確かめた版は Claude Code 2.1.308、Codex CLI 0.163.0（ソースは rust-v0.164.0）である。

## Claude Code のスキルの置き場と frontmatter

- 確認方法：https://code.claude.com/docs/en/skills.md（同ページの available string substitutions の節を含む）
- 確認の状態：確認済み
- 分かったこと：プロジェクトのスキルは `.claude/skills/<name>/SKILL.md` に置く。frontmatter の未知のキーは無視される。`${CLAUDE_SKILL_DIR}` が使える。SKILL.md は 500 行未満にする。一覧の description は 1536 文字で切り詰められる。`disable-model-invocation: true` で自動の起動を止める。skill の frontmatter に書いた hooks は呼び出しからセッションの終わりまで有効になる
- 使った決定：OUT-01、OUT-02、OUT-05、CTL-04

## Claude Code の hooks

- 確認方法：https://code.claude.com/docs/en/hooks.md と https://code.claude.com/docs/en/hooks-guide.md
- 確認の状態：確認済み
- 分かったこと：設定は `.claude/settings.json` の `hooks`。PreToolUse は `permissionDecision`（`allow`、`deny`、`ask`）で止められる。PostToolUse と Stop は `{"decision": "block", "reason": ...}` で AI に差し戻す。Stop には `stop_hook_active` が付く。`$CLAUDE_PROJECT_DIR` でプロジェクトのルートを参照できる。ファイル編集のツールは Edit、Write、MultiEdit、NotebookEdit で、`tool_input.file_path` に対象がある
- 使った決定：CTL-02、CTL-04、CTL-05

## Claude Code の非対話の実行と AGENTS.md

- 確認方法：https://code.claude.com/docs/en/headless.md、https://code.claude.com/docs/en/cli-reference.md、https://code.claude.com/docs/en/memory.md#agents-md
- 確認の状態：確認済み
- 分かったこと：`claude -p` で非対話に実行できる。`--output-format json`、`--permission-mode`、`--allowedTools`、`--no-session-persistence`、`--setting-sources project,local` が使える。AGENTS.md は CLAUDE.md が無いときだけ読まれるので、確実に読ませるには CLAUDE.md に `@AGENTS.md` と書く
- 使った決定：STEP-03（収束テストの runner）

## Codex のスキルの置き場

- 確認方法：https://learn.chatgpt.com/docs/build-skills と、Codex のソース（https://github.com/openai/codex/blob/rust-v0.164.0/codex-rs/）
- 確認の状態：確認済み
- 分かったこと：スキルは `.agents/skills` を作業ディレクトリからリポジトリのルートまで探す。ほかに `$HOME/.agents/skills` と `/etc/codex/skills` を探す。シンボリックリンクは辿る。name は 64 文字以内、一覧の description は 1024 文字で切り詰められる。明示の起動は `$<name>`
- 使った決定：OUT-01、OUT-05

## Codex の hooks と信頼

- 確認方法：https://learn.chatgpt.com/docs/hooks、https://learn.chatgpt.com/docs/config-file/config-reference、Codex のソース（rust-v0.164.0）
- 確認の状態：確認済み
- 分かったこと：設定は `.codex/hooks.json`。イベントは PreToolUse、PostToolUse、Stop、UserPromptSubmit を使える。ファイル編集は `apply_patch` で、`tool_input.command` がパッチの本文である。PreToolUse は deny だけを使える（ask は無い）。Stop の stdout は JSON でなければならず、`reason` は新しいユーザーの指示として扱われる。`CLAUDE_PROJECT_DIR` は無い。hooks は `/hooks` で信頼するまで実行されない。信頼のハッシュは宣言だけから計算される。プロジェクト自体が未信頼だと `.codex/` を読まない。`--dangerously-bypass-hook-trust` で一度だけ信頼を飛ばせる
- 使った決定：CTL-04、STEP-03（収束テストの runner）

## Codex の非対話の実行

- 確認方法：https://learn.chatgpt.com/docs/non-interactive-mode、https://learn.chatgpt.com/docs/developer-commands?surface=cli、`codex exec --help`（0.163.0）
- 確認の状態：確認済み
- 分かったこと：`codex exec` の既定のサンドボックスは読み取り専用で、承認は never に固定される。`--json`、`-C`、`--skip-git-repo-check`、`--ephemeral`、`--ignore-user-config`、`-o`、`--output-schema`、`--add-dir`、`--sandbox workspace-write` が使える。このマシンでは `codex` が PATH に無く、`~/.codex/packages/app-server-daemon/current/bin/codex` にある
- 使った決定：STEP-03（収束テストの runner）

## Codex の AGENTS.md

- 確認方法：https://learn.chatgpt.com/docs/agent-configuration/agents-md
- 確認の状態：確認済み
- 分かったこと：Codex はリポジトリのルートから作業ディレクトリまでの AGENTS.md を読む。スキルの手順は AGENTS.md ではなく SKILL.md に書き、スキルとして読ませる
- 使った決定：OUT-02
