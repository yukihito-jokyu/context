# 制御の段、出力の契約、違反例（フェーズ4・5）

決定を書いただけでは、AI はそれに従うとは限らない。従わせるには、決定ごとに「守らせ方」を選び、機械で確かめられる形にする。フェーズ4では守らせ方を作り、フェーズ5では違反例（probe）を流して、守らせ方が本当に AI を止めることを証明する。

この章は次の順に読む。1章で段を選び、2章で入力と出力の扱いの原則を確かめる。3章から5章で入力・出力（自動で直す format と、一緒に変える組を含む）・スクリプトを定義し、6章で手順を書き、7章で違反例とレビューの見本を作る。8章で、検査の側を変えて通す抜け道と、その塞ぎ方（封印を含む）を確かめる。

## 1. 守らせ方の段

決定ごとに、守らせ方の段を `control` に書く。段は、守ったかどうかを機械が確かめる段（`runtime`、`format`、`validate`）、値や形を渡すだけの段（`script`、`template`）、AI が確かめる段（`review`、`doc`）に分かれる。

| 段 | 意味 | 守ったかを確かめるもの | 決定に必要なもの |
|---|---|---|---|
| `runtime` | 共通ランタイム（`run.py`、`hook.py`、`install.py`）か、契約の `report.sections` が、AI の操作によらず行う・止める | 機械 | `how` に `run.py`・`hook.py`・`install.py`・`_skillrt.py`・`report.sections` のどれか。`probe.py` の標準の確認と配線が証明する |
| `format` | 検査の前に、契約の `format` が出力を自動で直す（4章） | 機械 | `outputs` の `format` でこの ID を使う。`probes` に、自動で直ることを確かめる違反例（`fixed` を持つもの。7章） |
| `validate` | 出力を契約で検査し、違反をルールID付きで返す | 機械 | 契約（`outputs` の `rule`、`checks` の `rule`、`together` の `rule`）でこの ID を使う。`probes` に違反例の ID を1つ以上 |
| `script` | AI に判断させず、スクリプトが値や材料を出す。AI がその値を使ったかは確かめない | — | `how` に実在する `scripts/<ファイル>`。単独では使わない |
| `template` | ひな形を写して埋めさせる | — | `how` に実在する `assets/<ファイル>`。単独では使わない |
| `review` | 完了前チェックリストに載せ、AI 自身に出力を確かめさせる | AI | `why_not_machine`。`dev/probes.json` の `reviews` に、機械の検査を通ってしまう違反の見本（7章） |
| `doc` | SKILL.md の手順か references に書くだけ | AI | `why_not_machine`。手順か references の本文にこの ID を書く |

段は、決定ごとに次の問いを上から順に当てて選び、当たった段をすべて `control` に入れる。選び方が AI ごとに分かれると、同じ決定でも守らせ方の強さが変わるからである。

1. 共通ランタイムが、AI の操作によらず行うか止めるか（標準の決定、`report.sections`）→ `runtime`
2. 違反を機械的に直せるか（行末の空白、末尾の改行、決まった置き換え、formatter）→ `format`
3. 出力の字面で判定できるか（置き場、件数、ファイル名、行の形、語、数、別のコマンドの結果）→ `validate`
4. AI が判断して出す値（数える、集める、並べる、区分する）を、スクリプトが代わりに出せるか → `script` を足す。script は値を渡すだけなので、1〜3 か 6〜7 の段と一緒に書く
5. 形を写させられるか → `template` を足す。script と同じく単独にしない
6. ここまでで機械が確かめる段が無く、違反が出力に痕跡として残る → `review`
7. 残らない（作業の順序、読んだもの、実行したコマンド、出力が無い状況での振る舞い）→ `doc`
8. review でも判定が割れる → 決定の文を書き直す。判定が割れる決定は揺れを止めない

字面で判定できるのに review に回さない。たとえば「1行目はチケットIDで始める」「`feat:` を付けない」は字面で判定できるので validate にする。

機械が確かめる段（runtime、format、validate）を含まない決定には、`why_not_machine` を「<種類>：<理由>」の形で書く。種類は次の3つのどれかである。理由を書けないなら、機械で確かめられる見込みがある。

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
| スキル自身のファイル | 実行中の変更をエラーにする | ハッシュの比較と hooks（CTL-02） |
| 契約の外のファイル | 実行中の作成・変更をエラーにする | git の作業ツリーの比較と hooks（CTL-05） |

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
| `ask`、`question` | 依頼に無ければ start の前に聞く。聞く文を `question` に書く |

入力ごとに、依頼に無いまま進めたときの影響を次の表で決め、`impact` に書く。表を上から順に当てはめ、最初に当たった行を使う。何でも聞くとユーザーの負担が大きく、何でも既定値で決めると取り返しのつかない選択を誤るからである。`skill_lint.py` が、`impact` と `ask`・`default` の組み合わせを確かめる。

| 依頼に無いまま進めたときの影響 | `impact` | 書くもの |
|---|---|---|
| 外に影響する、または取り消せない（送信、公開、削除、課金） | `external` | `ask` と `question` |
| 作業の対象か目的が決まらず、プロジェクトからも読み取れない | `target` | `ask` と `question` |
| 既定値で進めても、出力を作り直せば済む | `reversible` | `default`。報告の「既定値で決めた値」に載る |
| 上のどれでもない（無くても出力が決まる） | `optional` | `ask` も `default` も書かない |

どの入力を持つかは、[skill-profiles.md](skill-profiles.md) の種類の節の「入力の候補」から始める。候補は、その種類のスキルが利用者に聞くべき事項である（例：review の `target` は何をレビューするか）。候補ごとに、`inputs` に同じ key で入れるか、spec の `excluded_inputs` に `{"key": ..., "reason": ...}` で入れない理由を書く。`skill_lint.py` が、候補の漏れ、候補でない key、理由の無い除外、両方への記載を確かめる。候補の `impact` は目安であり、上の表で決め直してよい。

プロジェクトから機械的に読み取れる値（git の状態、設定ファイルの値）は、入力にしない。読み取るスクリプトを作る（5章）。

依頼が2通り以上に読めるときの扱いも、決定に書く。どちらを選ぶかで出力の形が大きく変わるなら、`target` と同じく聞く。そうでなければ、作るものが少ない方の読み方にし、報告の「既定値で決めた値」か「補足」に、そう読んだことを書く。

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
| `command` | `run` | `timeout`（秒、既定 60） | コマンドの終了コードが0であること |

すべての検査に、`rule`（必須）、`message`（違反の説明に足す文）、`stage` を書ける。`stage: "finish"` の検査は、編集の直後の hooks では実行せず、`run.py check`・`finish` と応答を終える前だけに実行する。時間のかかる検査に付ける。

`pattern` の中の `{in:キー}` は、入力の値（正規表現として安全な形）に置き換わる。`command` の `run` の中では、`{file}`（出力ファイル）、`{skill}`（スキルのディレクトリ）、`{root}`（プロジェクトのルート）、`{run}`、`{in:キー}` が置き換わる。コマンドが `<ルールID> <説明>` の形の行を出すと、その行がそのまま指摘になる。

出力ごとに `format` を書くと、`run.py check`・`finish` と hooks が、検査の前に出力を自動で直す（段 `format`）。直したことは check の出力に「整形 <ルールID> <パス> <説明>」の行で出て、報告の「検証」にも載る。AI に直させるより確実で、直し方が AI ごとに分かれない。

| `type` | 必須の項目 | 直すこと |
|---|---|---|
| `trailing_space` | — | 行末の空白とタブを消す |
| `final_newline` | — | 末尾の改行を1つにする |
| `replace` | `pattern`、`with` | 各行で正規表現 `pattern` に当たる部分を `with` に置き換える（`{in:キー}` も使える） |
| `command` | `run` | formatter のコマンドを実行する（置き換わる文字列は `command` 検査と同じ） |

すべてに `rule`（control に format を持つ決定の ID）を書く。`message` を書くと、整形の行の説明を置き換える。

一緒に変える出力の組（軸 O7）は、spec の `together` に `{"rule": "<決定のID>", "outputs": ["<出力ID>", "<出力ID>"], "message": "<説明>"}` の形で書く。組のうち一部の出力だけが start の後に変わっていると、check と finish が `rule` の指摘を出す。`rule` は control に validate を持つ決定にする。

`control` では次を決める。

| 項目 | 既定 | 意味 |
|---|---|---|
| `hooks` | `true` | Claude Code と Codex に hooks を登録する |
| `max_stop_blocks` | `3` | 応答の終了を差し戻す上限。超えると status を `failed` にする |
| `protected` | `SKILL.md`、`scripts/**`、`assets/**`、`references/**` | 実行中に変えてはいけないスキル自身のファイル（CTL-02） |
| `allow_changes` | `[]` | 出力のほかに変えてよいファイルの glob（CTL-05）。`**` だけは書けない |

## 5. スキル固有のスクリプト

AI に数えさせたり、集めさせたり、並べさせたりする処理は、スクリプトにする（段 `script`）。

- 置き場は `scripts/`、ファイル名は snake_case の `.py` か `.sh` にする
- Python は 3.9 以上の標準ライブラリだけを使う
- 先頭の docstring に、出力、終了コード、使い方を書く。`--help` で終了コード0になるようにする（`skill_lint.py` が確かめる）
- 終了コードは、0 成功、1 指摘あり、2 実行の誤り、3 質問が必要、4 以上はスキル固有の意味にする
- AI の判断を減らす値（件数、区分、並べ順）を、ラベル付きで出力する（例：「本文の単位: ファイル」）
- ネットワークに触れず、同じ入力なら同じ結果を出す。乱数、UUID、現在時刻を出力に入れない（日付が要るなら入力か git から取る）。数秒で終わるようにする。`skill_lint.py` は、ネットワークのモジュールの import をエラーに、乱数・UUID・現在時刻を警告にする
- 先頭の docstring に、そのスクリプトを `how` に挙げた決定の ID を書く。どの決定の `how` にも挙がっていないスクリプトは置かない。スクリプトから決定を辿れるようにするためで、`skill_lint.py` が確かめる
- 部品のファイル（`_` で始まる。例：`_changes.py`）は作らない。同じ処理が2つのスクリプトに要るなら、1つのスクリプトのサブコマンドにする。部品に分けるかどうかが作る AI ごとに分かれ、スクリプトの構成が揃わないからである。`skill_lint.py` が確かめる
- 共通ランタイム（`_skillrt.py`、`run.py`、`hook.py`、`install.py`）は書き換えない

## 6. 手順（SKILL.md の「2. 手順」）

SKILL.md のうち、手で書くのは「2. 手順」の番号付きの行だけである。ほかの節は `render_skill.py` が `dev/spec.json` から生成する。`skill_lint.py` が次を確かめる。

- 1 から連番で、5つ以上ある
- 1番目の手順は、start の前に質問を済ませる手順で、CTL-03 を含む
- `run.py start` → `run.py check` → `run.py finish` の順に並び、最後の手順は `run.py finish` である
- 各手順に、決定の ID か、`` ` `` で囲んだコマンドを含む。含む ID は decisions にある
- 1章の段に `doc` を含む決定の ID は、手順か references の本文に書く
- 使ってはいけない語（[variance-axes.md](variance-axes.md) の5章）を含まない
- 出力を書く手順に、写す元になる見本 `assets/examples/<ファイル>` を書く（7章）

## 7. 違反例（`dev/probes.json`）

違反例は、合格する出力（baseline）を決定に反する形に壊したものである。壊した出力で `run.py check` が終了コード1になり、出力が `expect` の正規表現に当たれば成功である。

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
| `baseline.fixture`、`setup` | 一時プロジェクトの元にするディレクトリと、start の前に1回実行するコマンド（`{skill}` は元のスキル、`{lab}` は一時ディレクトリ） |
| `baseline.input`、`text` | start に渡す入力と依頼文 |
| `baseline.files`、`commands` | start の後に毎回書くファイルと、実行するコマンド（`{skill}` は写したスキル、`{root}` はプロジェクト） |
| `files[].from` | 中身を `content` に書く代わりに、スキルの見本 `assets/examples/<ファイル>` を写す（`mode` が `create` か `replace` のときだけ） |
| `files[].mode` | `create`（中身を書く）、`replace`（`create` と同じ。既にあるファイルを書き換えることを示す）、`append`（末尾に足す）、`delete`（消す）、`sub`（`pattern` を `replacement` に置き換える） |
| `expect` | check の出力に当たるべき正規表現。ふつうはルールID |
| `fixed` | 段 format の違反例だけに書く。check の後の `files` の1つ目に、残ってはいけない正規表現 |
| `reviews` | 段 review の違反の見本。書式は違反例と同じで、`expect` は書かない。id は `<ルールID>-r<番号>` |

- validate を含む決定ごとに、違反例を1つ以上作る
- 見本（`assets/examples/`）には、検査に通る出力の実物を1つ以上置き、`baseline.files` の1つ以上を `from` でそれにする。こうすると、見本が検査に通ることを `probe.py` が毎回確かめる。手順で見本を示すと、AI は決定表の文から形を想像せずに、検査に通った実物を写せる。AI は規則より一番近い見本を写すので、見本には出力の決定を全部体現させる。出力が1つなら、見本のファイル名は出力のファイル名と同じにする。見本ごとに spec の `examples` に `{"path": "<assets/examples/ からの相対パス>", "shows": ["<体現する決定の ID>"]}` を書き、出力の決定（`OUT-*`）はすべて、どれかの見本の `shows` に入れる。`skill_lint.py` が、見本の有無、`examples` の記載と網羅、baseline の `from`、手順の記載を確かめる
- 違反の中身は、その決定の `bad` のように、AI が実際に書きそうなものにする
- 1つの違反例は、1つの決定だけを破る。baseline からの変更は、その決定を破るのに要る最小にする。別の決定の指摘も出ると、どの守らせ方が AI を止めたのかが分からなくなる。`probe.py` は、別のルールIDの指摘が出た違反例を `others` に記録し、`skill_lint.py --final` が警告にする
- 違反例が成功しない（check が落ちない）ときに、違反例の方を弱めて成功させない。検査（`checks`）か、決定の守らせ方を直す
- format を含む決定には、`fixed` を持つ違反例を作る。check が終了コード0で終わり、出力が `expect` に当たり、`files` の1つ目に `fixed` が残っていなければ成功である（例：`"fixed": "。$"`）
- review を含む決定（標準の決定を除く）には、`reviews` に違反の見本を1つ以上作る。`probe.py` は、見本が機械の検査を通ること（check が終了コード0）を確かめる。通らないなら、その違反は字面で判定できるので、段を validate にする。見本は収束テストの最後のラウンドで独立エージェントのレビューに渡し、完了前チェックリストで見つけられるか（検出率）を測る（[convergence-test.md](convergence-test.md) の3章と4章）
- `probe.py` は、違反例とレビューの見本に加えて標準の確認（CTL-01・02・03・05、RPT-01。CTL-02 は restart、hooks の登録、封印も、RPT-01 は abort も含む。8章）と、製品ごとの hooks の配線（登録、matcher、編集の後、応答を終える前、保護ファイルの編集の前、契約の外の編集、wait、実行していないとき、封印したスキルの編集の前）を確かめ、`dev/results/probe-results.json` に書く

## 8. 抜け道を塞ぐ

検査に通らないとき、AI は出力ではなく検査の側を変えて通そうとすることがある。これを抜け道と呼ぶ。共通ランタイムは次の表の抜け道を塞ぐ。塞ぎきれない部分は「残る穴」の列に書いた。スキルを作るときは、残る穴を新しい決定で塞ぐか、報告で見えることを確かめる。

| 抜け道 | 塞ぎ方 | 残る穴 |
|---|---|---|
| 編集ツールで保護ファイル・`state.json`・`report.md` を変える | hooks の PreToolUse が編集の前に止める（保護ファイルは Claude Code が ask、Codex が deny。実行記録はどちらも deny）。check と finish がハッシュを比べる（CTL-02） | Codex で hooks を信頼していなければ、check と finish の比較だけになる |
| Bash で保護ファイルを変える | hooks は Bash を止めない。check と finish がハッシュを比べる（CTL-02） | 変えてから元に戻すと見つからない。元に戻っているので出力への害は無い |
| 保護ファイルを変えてから `start --restart` で基準を取り直す | restart は、保護ファイルのハッシュ、hooks の登録、作業ツリー、履歴を最初の start から引き継ぐ。報告の「検証」に restart の回数が出る（CTL-02、CTL-05） | Bash で `.skill-runs/` ごと消してから start すると、記録も消える |
| abort してから start し、前の中断を隠す | 次の start が前の status と理由を `previous` に残し、報告の「検証」に出す | 同上（`.skill-runs/` の削除） |
| abort（か finish）の後、hooks が働かない間に保護ファイルを変え、start し直す | 封印したスキル（`assets/seal.json` がある）では、start が封印と比べ、違えば始めない（終了コード1。CTL-02）。封印する前（作っている途中）は、前の実行の記録と比べ、変わった保護ファイルを報告の「検証」に出す | 封印し直せば通る。ただし封印し直すには `skill_lint.py --final`（probe の結果を含む）に通る必要がある |
| 実行していない間に、編集ツールで封印したスキルの保護ファイルを変える | Claude Code では、PreToolUse の hook が人に確認を求める（CTL-04）。Codex には確認が無いので止めないが、次の start が封印と比べて止める | Bash での変更は hooks が止めない。次の start が封印と比べて止める |
| 契約の外のファイルを書く | check と finish が git の作業ツリーを比べる。PostToolUse が編集の直後に指摘する（CTL-05） | git が無いプロジェクトでは検査しない。報告の「検証」にそのことが出る |
| `assets/contract.json` を緩める | contract.json は保護ファイル（`assets/**`）なので、上の2行と同じに扱う（CTL-02） | なし |
| hooks の登録を外す | start が `.claude/settings.json` と `.codex/hooks.json` の登録を記録し、check と finish が比べる（CTL-02） | start の前に外されていれば、その実行では記録が無い。`install.py --check` で見つける |
| wait のまま応答を終える | wait の間は Stop の hook が止めないが、status は done にならず、報告の本文も出ない。次の発言で active に戻る | ユーザーが発言しなければ、その実行は検査されないまま残る |
| 報告を手で書く、要約する | finish と abort が同じ形の本文を出し、`report.md` に保存する（RPT-01） | 返答そのものは機械で比べない。`report.md` と見比べる |
| 検査を止める記法（lint の無効化コメント、テストの skip、CI を止める記法）を書く | 共通ランタイムは塞がない。軸 O8（検査を止める記法）の決定にし、`forbid` で禁じる。種類 generate と fix では重点軸なので対象外にできない（[skill-profiles.md](skill-profiles.md)） | O8 を対象外にすると塞がれない。対象外にするには `excluded_axes` に理由が要る |

`probe.py` は、このうち restart、hooks の登録、封印、実行の間の変更、abort を標準の確認として流す（`CTL-02-builtin-restart`、`CTL-02-builtin-hooks-<製品>`、`CTL-02-builtin-seal`、`CTL-02-builtin-between`、`RPT-01-builtin-abort`。配線の `pre-tool-sealed`）。収束テストでは、スキル自身や hooks の登録を変えたエージェントを失格にする（[convergence-test.md](convergence-test.md) の4章）。
