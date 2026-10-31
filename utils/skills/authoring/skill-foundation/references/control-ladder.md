# 制御の段、出力の契約、違反例（フェーズ4・5）

ルールを書いただけでは、AI はそれに従うとは限らない。従わせるには、ルールごとに「守らせ方」を選び、機械で確かめられる形にする。フェーズ4では守らせ方を作り、フェーズ5では違反例（probe）を流して、守らせ方が本当に AI を止めることを証明する。

この章は次の順に読む。1章で段を選び、2章で入力と出力の扱いの原則を確かめる。3章から5章で入力・出力（自動で直す format と、一緒に変える組を含む）・スクリプトを定義し、6章で手順を書き、7章で違反例とレビューの見本を作る。8章で、出力の検査と編集できる範囲を確かめる。

## 1. 守らせ方の段

ルールごとに、守らせ方の段を `control` に書く。段は、守ったかどうかを機械が確かめる段（`runtime`、`format`、`validate`）、値や形を渡すだけの段（`script`、`template`）、AI が確かめる段（`review`、`doc`）に分かれる。

| 段 | 意味 | 守ったかを確かめるもの | ルールに必要なもの |
|---|---|---|---|
| `runtime` | 共通ランタイム（`run.py`、`hook.py`、`install.py`、`feedback.py`、`feedback_review.py`）か、契約の `report.sections` が、AI の操作によらず行う・止める | 機械 | `how` に `run.py`・`hook.py`・`install.py`・`_skillrt.py`・`report.sections` のどれか。`probe.py` の標準の確認と hooks の動作の確認が証明する |
| `format` | 検査の前に、契約の `format` が出力を自動で直す（4章） | 機械 | `outputs` の `format` でこの ID を使う。`probes` に、自動で直ることを確かめる違反例（`fixed` を持つもの。7章） |
| `validate` | 出力を契約で検査し、違反をルールID付きで返す | 機械 | 契約（`outputs` の `rule`、`checks` の `rule`、`together` の `rule`）でこの ID を使う。`probes` に違反例の ID を1つ以上 |
| `script` | AI に判断させず、スクリプトが値や材料を出す。AI がその値を使ったかは確かめない | — | `how` に実在する `scripts/<ファイル>`。単独では使わない |
| `template` | ひな形を写して埋めさせる | — | `how` に実在する `assets/<ファイル>`。単独では使わない |
| `review` | 完了前チェックリストに載せ、AI 自身に出力を確かめさせる | AI | `why_not_machine`。`dev/probes.json` の `reviews` に、機械の検査を通ってしまう違反の見本（7章） |
| `doc` | SKILL.md の手順か references に書くだけ | AI | `why_not_machine`。手順か references の本文にこの ID を書く |

段は、ルールごとに次の問いを上から順に当てて選び、当たった段をすべて `control` に入れる。選び方が AI ごとに分かれると、同じルールでも守らせ方の強さが変わるからである。

1. 共通ランタイムが、AI の操作によらず行うか止めるか（標準のルール、`report.sections`）→ `runtime`
2. 違反を機械的に直せるか（行末の空白、末尾の改行、決まった置き換え、formatter）→ `format`
3. 出力の字面で判定できるか（置き場、件数、ファイル名、行の形、語、数、別のコマンドの結果）→ `validate`
4. AI が判断して出す値（数える、集める、並べる、区分する）を、スクリプトが代わりに出せるか → `script` を足す。script は値を渡すだけなので、1〜3 か 6〜7 の段と一緒に書く
5. 形を写させられるか → `template` を足す。script と同じく単独にしない
6. ここまでで機械が確かめる段が無く、違反が出力に痕跡として残る → `review`
7. 残らない（作業の順序、読んだもの、実行したコマンド、出力が無い状況での振る舞い）→ `doc`
8. review でも判定が割れる → ルールの文を書き直す。判定が割れるルールはばらつきを止めない

字面で判定できるのに review に回さない。たとえば「1行目はチケットIDで始める」「`feat:` を付けない」は字面で判定できるので validate にする。

機械が確かめる段（runtime、format、validate）を含まないルールには、`why_not_machine` を「<種類>：<理由>」の形で書く。種類は次の3つのどれかである。理由を書けないなら、機械で確かめられる見込みがある。

| 種類（`why_not_machine` の先頭） | 意味 | 段 |
|---|---|---|
| `痕跡が残らない` | 違反が出力に残らない（順序、読んだもの、実行したコマンド、中断） | `doc`。出力を見ても判定できないので `review` にしない |
| `意味の判断が要る` | 違反は出力に残るが、字面では判定できない（言語、内容が材料と合っているか） | `review` を含める |
| `費用が見合わない` | 判定する仕組みは作れるが、決まり1つのためには大きい | `review` か `doc` |

`skill_lint.py` が、段の名前、script と template を単独で使っていないこと、`why_not_machine` の種類と段の組み合わせ、段ごとに必要なものを確かめる。

## 2. 入力に寛容、出力に厳格

縛る対象は AI の出力である。ユーザーの入力は縛らない。

| 対象 | 扱い | 仕組み |
|---|---|---|
| 入力のキー | 表記ゆれ・別名・全角・大文字と小文字・`-` と `_` の違いを受け入れる | `run.py start`（`aliases` と正規化） |
| 入力の値 | 型に変換し、`case` で揃える。変換できなければ既定値で補い、警告として記録する | `run.py start` |
| 足りない入力 | `default` で補い、報告の「既定値で決めた値」に載せる。`ask` なら start の前に聞く | `run.py start`（終了コード3） |
| 未知のキー | 捨てずに `extra` として記録する | `run.py start` |
| ユーザーの発言 | 止めない、書き換えない | hooks の UserPromptSubmit（CTL-04） |
| 出力の置き場・件数・中身 | 契約に合わなければルールID付きのエラーにする | `run.py check`・`finish`、hooks |
| スキル自身のファイル | ユーザーの依頼に従って変更できる | 変更を理由に開始や完了を止めない |

スキル固有のスクリプトも同じ原則で作る。引数とファイルの形には寛容にし、AI が書いた出力の検査では厳格にする。

## 3. 入力の定義（`inputs`）

| 項目 | 書くこと |
|---|---|
| `key` | snake_case のキー |
| `label` | 表示名 |
| `type` | `string`、`int`、`bool`、`list`（`,` `、` 改行で区切る）、`enum`、`path`、`slug` のどれか |
| `enum`、`enum_aliases` | `enum` の選択肢と、選択肢の別名（例：`{"日本語": "ja"}`） |
| `case` | `upper` か `lower`。文字列を揃える |
| `aliases` | キーの別名（日本語の呼び方、英語の呼び方） |
| `impact` | 依頼に無いまま進めたときの影響。下の表の値 |
| `default` | 既定値。`ask` と同時には書かない |
| `default_by` | 前にある入力の値で既定値を変える対応。`{"input": "targets", "values": {"codex": ".agents/skills"}}` なら、`targets` が `codex` のとき既定値を `.agents/skills` にする。どの値にも当たらなければ `default` を使う |
| `ask`、`question` | 依頼に無ければ start の前に聞く。聞く文を `question` に書く |

スキルの直下に `settings/` を置くと、依頼に無い入力を `default` より先に設定で補える。`run.py start` は `settings/user-setting.yaml`（ユーザーの設定）、`settings/skill-setting.yaml`（スキルの設定）の `inputs` の順に、null でない最初の値を使い、出どころを start の出力と報告の「既定値で決めた値」に出す。依頼文から推した値は `start --guess <キー>=<値>` で渡し、設定より弱く、`default_by` と `default` より強い。設定のファイルは YAML で書き、`#` から行末までのコメントで値の右に書き方を添えられる。読めるのは字下げの入れ子のマップ、`- 値` と `[a, b]` の一覧、null・真偽・数・文字列で、`run.py` が標準ライブラリだけで読む。

入力ごとに、依頼に無いまま進めたときの影響を次の表で決め、`impact` に書く。表を上から順に当てはめ、最初に当たった行を使う。何でも聞くとユーザーの負担が大きく、何でも既定値で決めると取り返しのつかない選択を誤るからである。`skill_lint.py` が、`impact` と `ask`・`default` の組み合わせを確かめる。

| 依頼に無いまま進めたときの影響 | `impact` | 書くもの |
|---|---|---|
| 外に影響する、または取り消せない（送信、公開、削除、課金） | `external` | `ask` と `question` |
| 作業の対象か目的が決まらず、プロジェクトからも読み取れない | `target` | `ask` と `question` |
| 既定値で進めても、出力を作り直せば済む | `reversible` | `default`。報告の「既定値で決めた値」に載る |
| 上のどれでもない（無くても出力が決まる） | `optional` | `ask` も `default` も書かない |

どの入力を持つかは、[skill-profiles.md](skill-profiles.md) の種類の節の「入力の候補」から始める。候補は、その種類のスキルが利用者に聞くべき事項である（例：review の `target` は何をレビューするか）。候補ごとに、`inputs` に同じ key で入れるか、spec の `excluded_inputs` に `{"key": ..., "reason": ...}` で入れない理由を書く。`skill_lint.py` が、候補の漏れ、候補でない key、理由の無い除外、両方への記載を確かめる。候補の `impact` は目安であり、上の表で決め直してよい。

プロジェクトから機械的に読み取れる値（git の状態、設定ファイルの値）は、入力にしない。読み取るスクリプトを作る（5章）。

依頼が2通り以上に読めるときの扱いも、ルールに書く。どちらを選ぶかで出力の形が大きく変わるなら、`target` と同じく聞く。そうでなければ、作るものが少ない方の読み方にし、報告の「既定値で決めた値」か「補足」に、そう読んだことを書く。

## 4. 出力の契約（`outputs`）

出力の置き場は、次の表で決める。表の上から順に当てはめ、最初に当たった行を使う。既存のファイルを書き換えるかどうかが作る AI ごとに分かれると、出力の数も検査も変わるからである。

| 依頼の言い方 | 出力の置き場 |
|---|---|
| 既存のファイルを書き換えること自体を求める（「〜を更新して」「〜に書き込んで」「〜を直して」） | そのファイル |
| 上のどれでもない（「〜に足す〇〇を書いて」「〜用の〇〇を作って」） | `{run}/out/<ファイル名>`。既存のファイルへの反映は利用者に任せ、手順の最後の返答で写し方を示す |

出力ごとに次を書く。返答の本文が成果物のスキルでも、本文を `{run}/out/` のファイルに書かせて検査し、`report.include_output` にその出力の ID を書く。

| 項目 | 書くこと |
|---|---|
| `id` | kebab-case の ID。出力が1つなら、スキルの名前の目的語（`write-commit-message` なら `commit-message`）にする |
| `label` | 表示名 |
| `path` | プロジェクトのルートからの相対の glob。`{run}` は `.skill-runs/<name>`、`{in:キー}` は入力の値になる。`count` の `max` が 1 なら glob にせず、ファイル名まで書く。出力が1つで `{run}/out/` に書くなら、ファイル名は `<id>.<拡張子>` にする（`skill_lint.py` が確かめる） |
| `rule` | 置き場と件数の違反に付けるルールID |
| `count` | `{"min": 1, "max": 1}` の形の件数 |
| `name_pattern` | ファイル名の正規表現 |
| `checks` | 中身の検査の配列（次の表） |

| `type` | 必須の項目 | 任意の項目 | 確かめること |
|---|---|---|---|
| `headings` | `equals` か `includes` | `level` | 見出しの一致、または順序どおりに含むこと |
| `require` | `pattern` | `lines`（`all`、`first`、行番号の配列）、`min`、`max`、`ignore_code`、`multiline` | 正規表現に当たる行の数 |
| `forbid` | `pattern` | `lines`、`ignore_code`、`multiline` | 正規表現に当たる行が無いこと |
| `max_lines`、`min_lines` | `value` | — | 行数 |
| `line_length` | `max` | `lines` | 1行の文字数 |
| `json_schema` | `schema` | — | JSON の型、必須のキー、列挙値 |
| `front_matter` | `required_keys` | — | 先頭の `---` の中のキー |
| `command` | `run` | `timeout`（秒、既定 60）、`rules`（コマンドが出しうる、`rule` 以外のルールID の配列） | コマンドの終了コードが0であること |

すべての検査に、`rule`（必須）、`message`（違反の説明に足す文）、`stage` を書ける。`stage: "finish"` の検査は、編集の直後の hooks では実行せず、`run.py check`・`finish` と応答を終える前だけに実行する。時間のかかる検査に付ける。

`pattern` の中の `{in:キー}` は、入力の値（正規表現として安全な形）に置き換わる。`command` の `run` の中では、`{file}`（出力ファイル）、`{skill}`（スキルのディレクトリ）、`{root}`（プロジェクトのルート）、`{run}`、`{in:キー}` が、シェルで安全な形（引用符付き）に置き換わる。`run` はシェルで、プロジェクトのルートを作業ディレクトリにして実行する。

- 終了コードが0なら、出力に何があっても指摘にしない
- 0以外なら、出力のうち `<ルールID> <説明>` の形の行（ルールID は大文字2〜6字、`-`、数字2〜3桁）が、そのまま指摘になる。そういう行が無ければ、`rule` の「検査コマンドが失敗しました」の指摘になる
- `rule` 以外のルールID の行を出すなら、そのルールID を `rules` に書く。書かないと、`skill_lint.py` が「契約で使われていない」エラーにする

報告に節を足すとき（スキルが自分の結果を集計して見せるとき）は、spec の `report.sections` に `{"run": "<コマンド>", "timeout": <秒>}` を書く。`"stage": "finish"` を付けると、`finish` だけが実行する。動きは [runtime.md](runtime.md) の4章にある。

出力ごとに `format` を書くと、`run.py check`・`finish` と hooks が、検査の前に出力を自動で直す（段 `format`）。直したことは check の出力に「整形 <ルールID> <パス> <説明>」の行で出て、報告の「検証」にも載る。AI に直させるより確実で、直し方が AI ごとに分かれない。

| `type` | 必須の項目 | 直すこと |
|---|---|---|
| `trailing_space` | — | 行末の空白とタブを消す |
| `final_newline` | — | 末尾の改行を1つにする |
| `replace` | `pattern`、`with` | 各行で正規表現 `pattern` に当たる部分を `with` に置き換える（`{in:キー}` も使える） |
| `command` | `run` | formatter のコマンドを実行する（置き換わる文字列は `command` 検査と同じ） |

すべてに `rule`（control に format を持つルールID）を書く。`message` を書くと、整形の行の説明を置き換える。

一緒に変える出力の組（軸 O7）は、spec の `together` に `{"rule": "<ルールID>", "outputs": ["<出力ID>", "<出力ID>"], "message": "<説明>"}` の形で書く。組のうち一部の出力だけが start の後に変わっていると、check と finish が `rule` の指摘を出す。`rule` は control に validate を持つルールにする。

`control` では次を決める。

| 項目 | 既定 | 意味 |
|---|---|---|
| `hooks` | `true` | Claude Code と Codex に hooks を登録する |
| `max_stop_blocks` | `3` | 応答の終了を差し戻す上限。超えると status を `failed` にする |

## 5. スキル固有のスクリプト

AI に数えさせたり、集めさせたり、並べさせたりする処理は、スクリプトにする（段 `script`）。

- 置き場は `scripts/`、ファイル名は snake_case の `.py` か `.sh` にする
- Python は 3.9 以上の標準ライブラリだけを使う
- 先頭の docstring に、出力、終了コード、使い方を書く。`--help` で終了コード0になるようにする（`skill_lint.py` が確かめる）
- 終了コードは、0 成功、1 指摘あり、2 実行の誤り、3 質問が必要、4 以上はスキル固有の意味にする
- AI の判断を減らす値（件数、区分、並べ順）を、ラベル付きで出力する（例：「本文の単位: ファイル」）
- ネットワークに触れず、同じ入力なら同じ結果を出す。乱数、UUID、現在時刻を出力に入れない（日付が要るなら入力か git から取る）。数秒で終わるようにする。`skill_lint.py` は、ネットワークのモジュールの import をエラーに、乱数・UUID・現在時刻を警告にする
- 先頭の docstring に、そのスクリプトを `how` に挙げたルールID を書く。どのルールの `how` にも挙がっていないスクリプトは置かない。スクリプトからルールを辿れるようにするためで、`skill_lint.py` が確かめる
- 部品のファイル（`_` で始まる。例：`_changes.py`）は作らない。同じ処理が2つのスクリプトに要るなら、1つのスクリプトのサブコマンドにする。部品に分けるかどうかが作る AI ごとに分かれ、スクリプトの構成が揃わないからである。`skill_lint.py` が確かめる
- 共通ランタイム（`_skillrt.py`、`run.py`、`hook.py`、`install.py`、`feedback.py`、`feedback_review.py`）は書き換えない
- 入力の値とプロジェクトのルートは、引数で受け取る。`checks` の `run` や手順のコマンドに `{in:キー}`・`{root}` を書いて渡す（4章）
- 試すときは、試しのプロジェクトを手で作らない。スクリプトの分かれ道（指摘を出す場合、出さない場合）ごとに違反例（7章）を作り、`probe.py` で流す。一時プロジェクトの中を見たいときは、`probe.py <スキル> --only <違反例ID> --keep-temp` で残し、見終えたら消す。スキルのディレクトリ（`dev/` を含む）や `.skill-runs/` に試しのプロジェクトを置かない。手で試した分かれ道は記録に残らず、次に直したときに確かめ直されないからである

## 6. 手順（SKILL.md の「2. 手順」）

SKILL.md のうち、手で書くのは「2. 手順」の番号付きの行だけである。ほかの節は `render_skill.py` が `dev/spec.json` から生成する。`skill_lint.py` が次を確かめる。

- 1 から連番で、5つ以上ある
- 1番目の手順は、start の前に質問を済ませる手順で、CTL-03 を含む
- `run.py start` → `run.py check` → `run.py finish` の順に並び、最後の手順は `run.py finish` である
- 各手順に、ルールID か、`` ` `` で囲んだコマンドを含む。含む ID は decisions にある
- 1章の段に `doc` を含むルールID は、手順か references の本文に書く
- 使ってはいけない語（[variance-axes.md](variance-axes.md) の5章）を含まない
- 出力を書く手順に、写す元になる見本 `assets/examples/<ファイル>` を書く（7章）

## 7. 違反例（`dev/probes.json`）

違反例は、合格する出力（baseline）をルールに反する形に壊したものである。壊した出力で `run.py check` が終了コード1になり、出力が `expect` の正規表現に当たれば成功である。

```json
{
  "baseline": {
    "fixture": "dev/fixtures/basic",
    "setup": ["git add -A"],
    "input": {"ticket": "abc-12"},
    "text": "ABC-12 のコミットメッセージを書いて",
    "files": [{"path": "{run}/out/commit-message.txt", "from": "assets/examples/commit-message.txt"}],
    "commands": []
  },
  "probes": [
    {"id": "OUT-02-a", "rule": "OUT-02", "description": "Conventional Commits の接頭辞を付ける",
     "files": [{"path": "{run}/out/commit-message.txt", "mode": "create", "content": "ABC-12 feat: 引き算を足す\n"}],
     "expect": "OUT-02"}
  ]
}
```

| 項目 | 意味 |
|---|---|
| `baseline.fixture`、`setup` | 一時プロジェクトの元にするディレクトリと、start の前に1回実行するコマンド（`{skill}` は元のスキル、`{lab}` は一時ディレクトリ）。作られ方は表の下に書く |
| `baseline.input`、`text` | start に渡す入力と依頼文 |
| `baseline.files`、`commands` | start の後に毎回書くファイルと、実行するコマンド（`{skill}` は写したスキル、`{root}` はプロジェクト） |
| `files[].from` | 中身を `content` に書く代わりに、スキルの見本 `assets/examples/<ファイル>` を写す（`mode` が `create` か `replace` のときだけ） |
| `files[].mode` | `create`（中身を書く）、`replace`（`create` と同じ。既にあるファイルを書き換えることを示す）、`append`（末尾に足す）、`delete`（消す）、`sub`（`pattern` を `replacement` に置き換える） |
| `expect` | check の出力に当たるべき正規表現。ふつうはルールID |
| `fixed` | 段 format の違反例だけに書く。check の後の `files` の1つ目に、残ってはいけない正規表現 |
| `reviews` | 段 review の違反の見本。書式は違反例と同じで、`expect` は書かない。id は `<ルールID>-r<番号>` |

`probe.py` は、一時プロジェクトを最初に1回だけ、次の順で作る。違反例ごとには、start し直し、`baseline.files`・`commands` と違反例の `files` を書いて check し、書く前の中身に戻す。

1. `baseline.fixture` を写す（無ければ空のディレクトリを作る）
2. `git init` し、すべてのファイルを `base` としてコミットする
3. `baseline.setup` を、プロジェクトのルートで実行する
4. スキルを写し（`dev/` は写さない）、`install.py` で置き場所と hooks を登録する
5. `baseline.input` と `text` で start し、`baseline.files` と `commands` を実行する

- `setup` では `git commit` しない。fixture は既にコミット済みなので、変更が無ければ commit は失敗する。コミットに載せない変更（ステージした変更、未追跡のファイル）を作るのが `setup` の役目である
- fixture の中の `.gitignore` に当たるファイルは、2のコミットに入らない
- `files[].mode` が `sub` で、`pattern` が1回も当たらないと、`probe.py` はそこで止まる（終了コード2）
- 収束テストの一時プロジェクト（[convergence-test.md](convergence-test.md) の1章）も、fixture を写す → git の初回コミット → `setup` の順で作る。違いは、スキルを写すのが初回コミットの前であること

- validate を含むルールごとに、違反例を1つ以上作る
- 見本（`assets/examples/`）には、検査に通る出力の実物を1つ以上置き、`baseline.files` の1つ以上を `from` でそれにする。こうすると、見本が検査に通ることを `probe.py` が毎回確かめる。手順で見本を示すと、AI はルールの文から形を想像せずに、検査に通った実物を写せる。AI はルールの文より一番近い見本を写すので、見本には出力のルールを全部体現させる。出力が1つなら、見本のファイル名は出力のファイル名と同じにする。見本ごとに spec の `examples` に `{"path": "<assets/examples/ からの相対パス>", "shows": ["<体現するルールID>"]}` を書き、出力のルール（`OUT-*`）はすべて、どれかの見本の `shows` に入れる。`skill_lint.py` が、見本の有無、`examples` の記載と網羅、baseline の `from`、手順の記載を確かめる
- 違反の中身は、そのルールの `bad` のように、AI が実際に書きそうなものにする
- 1つの違反例は、1つのルールだけを破る。baseline からの変更は、そのルールを破るのに要る最小にする。別のルールの指摘も出ると、どの守らせ方が AI を止めたのかが分からなくなる。`probe.py` は、別のルールIDの指摘が出た違反例を `others` に記録し、`skill_lint.py --final` が警告にする
- 違反例が成功しない（check が落ちない）ときに、違反例の方を弱めて成功させない。検査（`checks`）か、ルールの守らせ方を直す
- format を含むルールには、`fixed` を持つ違反例を作る。check が終了コード0で終わり、出力が `expect` に当たり、`files` の1つ目に `fixed` が残っていなければ成功である（例：`"fixed": "。$"`）
- review を含むルール（標準のルールを除く）には、`reviews` に違反の見本を1つ以上作る。`probe.py` は、見本が機械の検査を通ること（check が終了コード0）を確かめる。通らないなら、その違反は字面で判定できるので、段を validate にする。見本は収束テストの最後のラウンドで独立エージェントのレビューに渡し、完了前チェックリストで見つけられるか（検出率）を測る（[convergence-test.md](convergence-test.md) の3章と4章）
- `probe.py` は、違反例・レビューの見本・開始と完了・質問待ち・報告の形・製品ごとの hooks を確かめる。スキル自身や hooks を変更した後も実行できることを確かめ、`dev/results/probe-results.json` に書く。

## 8. 出力の検査と編集できる範囲

出力の契約は `check`、`finish`、hooks が検査する。スキル自身のファイルと hooks の設定は、ユーザーの依頼に従って変更できる。変更を理由に実行を拒否せず、変更後に特別な手順を要求しない。

| 対象 | 扱い |
|---|---|
| スキルの本文・ルール・契約・スクリプト・設定 | 実行中も編集できる。出力は現在の契約で検査する |
| hooks の登録 | 変更できる。登録の有無は `install.py --check` で確認できる |
| `.skill-runs/<name>/state.json`・`report.md` | run.py が管理する実行記録。実行中の編集ツールによる直接の編集を拒否する |
| 契約に合わない出力 | `check` と `finish` が指摘する。hooks が有効なら編集後と応答を終える前にも検査する |
| 独立エージェントの作業ディレクトリ制限 | fence.py が管理する。スキルの微修正とは別に、作業範囲の外への操作を制限する |

`probe.py` は、スキルを変更した後も `start`・`check`・`finish` が通ることと、不正な出力を検査が検出することを確かめる。


## 9. 利用中の指摘と承認の収集

生成するスキルには [feedback.md](feedback.md) の収集 hooks を追加機能として必ず同梱し、既定で登録する。生成した SKILL.md・ルール表・チェックリストには収集の指示や専用ルールを入れない。必要な指示は有効な hooks だけが注入する。hooks を無効にしてもスキル本来の処理が完了し、収集側の失敗も本来の処理を止めない。共通の assets/feedback.schema.json で、指摘・修正前後・確認画面でのユーザー承認・使ったスキルの版を保存する。承認済みの事例を export し、評価基準の合意を得てから Eval と収束テストへ使う。
