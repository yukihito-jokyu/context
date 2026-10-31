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

Context Repository のように共通スキルを正本管理する場合は、本体をプロジェクト内の `utils/skills/.../<name>/` に保持し、`install.py` で対象製品すべての標準の置き場を本体への相対シンボリックリンクにする。`skill_lint.py --final --project` は、本体の実体がプロジェクト内の `utils/skills/` 配下にあり、各置き場のリンクが同じ本体へ解決されるとき、この配置も認める。リンクが無い、複製や異なる場所を指している、本体がプロジェクト外や `utils/skills/` 以外にある場合は、この共有正本の配置として認めない。hooks は通常配置と同じく `install.py --check` で検査する。

## 2. hooks

hooks は、AI がファイルを編集した後、応答を終える前、実行記録を編集する前に、`scripts/hook.py` を実行する仕組みである。製品ごとの入力と出力の形の違いは、`hook.py --platform claude|codex` が吸収する。

| 項目 | Claude Code | Codex |
|---|---|---|
| 設定ファイル | `.claude/settings.json` | `.codex/hooks.json` |
| 使うイベント | PreToolUse、PostToolUse、Stop、UserPromptSubmit | 同じ |
| ファイル編集のツール | `Edit`、`Write`、`MultiEdit`、`NotebookEdit`（`tool_input.file_path`） | `apply_patch`（`tool_input.command` のパッチ本文の `*** Add File:`、`*** Update File:`、`*** Delete File:`、`*** Move to:` の行） |
| 実行記録・指摘と承認の記録への直接の編集 | `permissionDecision: "deny"` | 同じ |
| スキル自身のファイルの編集 | 実行中も実行していないときも止めない | 同じ |
| 編集の後と終える前の差し戻し | `{"decision": "block", "reason": ...}` | 同じ。Stop の `reason` は新しいユーザーの指示として扱われる |
| Stop の出力 | JSON か空 | JSON でなければならない |
| 差し戻しの回数 | `hook.py` が `state.json` の `stop_blocks` で数える（製品の仕組みに頼らない） | 同じ |
| プロジェクトのルート | `$CLAUDE_PROJECT_DIR` | 変数が無いので `git rev-parse --show-toplevel` か `pwd` を使う |
| 実行の条件 | 設定を読めば実行する | `/hooks` で利用者が信頼するまで実行しない。プロジェクト自体が未信頼だと `.codex/` を読まない |

Codex の信頼は、hooks の宣言（コマンドの文字列）から計算する。呼び出すスクリプトの中身を変えても信頼は外れない。`install.py` は宣言を毎回同じ文字列で書くので、一度信頼すればスキルを作り直しても信頼し直す必要は無い。

`install.py` は既存の設定を残し、このスキルの項目だけを足す。同じ項目が既にあれば何もしない。`--uninstall` で自分の項目だけを外す。

作ったスキルをプラグインで配るときは、本体を `<プラグイン>/skills/<name>/` に移し、プロジェクトの置き場（`.claude/skills`、`.agents/skills`）には置かない。hooks もプロジェクトに登録せず、プラグインに書く。Claude Code は `hooks/hooks.json`（`${CLAUDE_PLUGIN_ROOT}` で本体を指す）、Codex は `.codex-plugin/plugin.json` の `hooks`（`${PLUGIN_ROOT}`）に、上の4つのイベントで `hook.py --platform claude|codex` を呼ぶ項目を書く。`skill_lint.py --final --project` は、この形のときは置き場に本体と別のものが無いことと、プラグインの hooks を確かめる。`catalog.py` は、プロジェクトのマーケットプレイス（`.claude-plugin/marketplace.json`、`.agents/plugins/marketplace.json`）に載るプラグインのスキルも載せる。スキルと hooks は、利用者がプラグインを入れたときだけ使える。

成果物への指摘は UserPromptSubmit の `prompt` から記録する。修正前後の確認画面で承認した版だけを共通形式へ確定する。両製品とも [feedback.md](feedback.md) に従う。

## 3. 収束テストの起動方法

収束テストでは、作成に関わっていない独立エージェントを、会話の履歴を持たない状態で起動する。`convergence.py run` の既定のコマンドは次のとおりである。`{prompt}` と `{dir}` が置き換わる。spec の `convergence.runner_commands` で上書きできる。上書きしていなければ、設定のモデルと推論エフォート（[convergence-test.md](convergence-test.md) の3章）を、`claude` は `--model`・`--effort`、`codex` は `-m`・`-c model_reasoning_effort="<値>"` で足す。

| runner | コマンド | 理由 |
|---|---|---|
| `claude` | `claude -p {prompt} --output-format stream-json --verbose --permission-mode acceptEdits --no-session-persistence --setting-sources project,local --allowedTools <一覧>` | ユーザー単位の設定（グローバルの指示と hooks）を読ませず、プロジェクトの設定だけで動かす。stream-json は道具の呼び出しを1行ずつ出すので、セッションの記録を残さなくても動きを分析できる |
| `codex` | `codex exec --json --sandbox workspace-write --skip-git-repo-check --ephemeral --dangerously-bypass-hook-trust -c projects."{dir}".trust_level="trusted" -c sandbox_workspace_write.exclude_slash_tmp=true -c sandbox_workspace_write.exclude_tmpdir_env_var=true -C {dir} -o <最後の発言> {prompt}` | 一時プロジェクトの hooks は `/hooks` の信頼の手続きを経ていないため、このテストに限って信頼を飛ばす。`/tmp` と `$TMPDIR` を書き込み先から外し、作業ディレクトリの外への書き込みをサンドボックスで止める |
| `subagent` | 起動しない。`convergence.py prompts` が出したプロンプトを、呼び出し元の AI が Agent ツールで専用のエージェント型 `skill-foundation-tester` に渡す | 上の2つを起動できない環境での代わり。スキルの hooks が働かないなどの限界は [convergence-test.md](convergence-test.md) の3章 |

- `codex` が PATH に無いときは、`$CODEX_HOME/packages/*/current/bin/codex` を探す。環境変数 `SKILL_FOUNDATION_CODEX` でパスを指定できる
- `codex exec` の既定のサンドボックスは読み取り専用なので、`--sandbox workspace-write` を付ける
- `--ephemeral` でセッションの記録を残さないので、`run` が `--json` の出力を行ごとに届いた時刻を付けて保存し、`trace` がエージェントの動きを読む（[convergence-test.md](convergence-test.md) の7章）
- どの runner でも、作業ディレクトリの外への操作は `fence.py` が止める。runner `claude`・`codex` では、`run` が環境変数 `TMPDIR` を一時プロジェクトの `.skill-runs/_fence/tmp` に向ける（[convergence-test.md](convergence-test.md) の3章）
- Claude Code の `--setting-sources project,local` は、ユーザーのグローバルの CLAUDE.md を読ませないためである。グローバルの指示がテストの結果に混ざると、スキルの効果を測れない
