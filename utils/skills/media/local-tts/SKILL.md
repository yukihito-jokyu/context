---
name: local-tts
description: スライドや検査済み原稿を伴わない、ローカルの音声合成（VoxCPM2、OmniVoice、Fish Audio S2 Pro）を運用する。文章をその場で読み上げる、テキストやSSMLをWAVにする、録音から声をクローンして登録・一覧・作り直し・削除する、エンジンの導入と切り替え、TTSサーバーを起動・停止する、OpenAI互換の音声API（/v1/audio/speech）を立てる、不調を切り分ける、旧presenter-ttsフォルダからの移し替え、キャッシュの片付けに使う。「読み上げて」「音声にして」「WAVにして」「この声で話して」「声を登録して」「OmniVoiceで」「VoxCPM2で」「S2で」「TTSサーバーを止めて」「ローカルTTS」「音声APIを立てて」では、スキル名を言われなくてもこのスキルを使う。html-deckのスライドにナレーションを付ける、player.htmlやMP4を作る場合はpresenter、発表原稿の作成や検査はpresentation-ja、別PCのAPIを使う場合はremote-ttsを使う。
license: MIT
compatibility: Apple Silicon Mac（OmniVoice・VoxCPM2はMPS、S2はMetal）、またはWindows 10/11＋NVIDIA GPU（OmniVoice・VoxCPM2はCUDA 12.8版PyTorch、S2はCUDA 12.4以上でビルド）。uv、FFmpegが必要。導入時にHugging Face接続、S2のビルドにはGit、CMake、WindowsはVisual Studio C++、MacはXcode Command Line Tools、GitHub接続が必要。
---

# local-tts

ローカルの音声合成で、文章を声にする。外部のAPIには送らない。

コードは同梱の`tools/`（uvのプロジェクト、パッケージ名`local_tts`）にある。
`<local-tts>`をこのSKILL.mdのあるフォルダとして、すべて次の形で呼ぶ。パスに空白が入ることがあるので引用符で囲む。

```console
uv run --project "<local-tts>/tools" local-tts <command> ...
```

初回の呼び出しでuvが依存関係をそろえるので、`uv sync`は不要。

エンジン、モデル、声、設定は`<home>`（Macは`~/.local/share/local-tts`、Windowsは`%LOCALAPPDATA%\local-tts`、`LOCAL_TTS_HOME`で変更可）にある。presenterスキルの`presenter-tts`フォルダとは別で、共有しない。
旧フォルダ（`~/.local/share/presenter-tts`、`%LOCALAPPDATA%\presenter-tts`）に声が残っているときは、コマンドが止まって案内する。[移し替え](references/commands.md#8-データのフォルダhome)の`home migrate`で移す。声を扱うので、`--dry-run`の結果を見せて承認を得てから実行する。

## 1. エンジンを選ぶ

| エンジン | このMac（M4）での速さ | メモリ | 向いている用途 | ライセンス |
|---|---|---|---|---|
| `voxcpm2`（既定） | 音声の約1.9〜2.4倍の時間 | 約14 GB（CUDAは約8 GB） | 生成しながら届き、最初の音が早い（約1分の原稿で4.6秒） | Apache-2.0 |
| `omnivoice` | 約1.9〜2.0倍 | 約4 GB | メモリが少ない環境。1回の生成が長いほど速い（最初の音は遅い） | Apache-2.0 |
| `s2` | 約8倍 | 約4 GB | 以前の音声と声をそろえたいとき | 研究・非商用（商用は別契約） |
| `voicevox` | — | — | 自分で起動したVOICEVOX ENGINEにつなぐ | キャラクターごと |

- 指定しなければ設定の`engine`（なければVoxCPM2）。コマンドごとに`--engine <名前>`で変える。
- 状態は`engine list`で確かめる。PyTorchのエンジンは`engine install <名前>`で導入する（実行環境約1〜1.5 GBとモデル約3〜5 GBをダウンロードするので、承認を得てから）。
- 詳しい計測値と仕組みは[エンジンの詳細](references/engines.md)にある。

## 2. 動く状態か確かめる

```console
uv run --project "<local-tts>/tools" local-tts doctor
uv run --project "<local-tts>/tools" local-tts engine list
```

使うエンジンが`ready`でなければ、[セットアップ手順](references/setup.md)に従う。ソフトの導入（S2はライセンスへの同意も）の承認が必要なので、勝手に進めない。
エンジンのサーバーは`say`・`speak`・`api`が自動で起動するので、手動で起動しなくてよい。

## 3. 目的からコマンドを選ぶ

| 目的 | コマンド | 補足 |
|---|---|---|
| いま声で聞きたい | `say "文章"` | 生成しながらスピーカーで再生する。`outputs/say.wav`にも残る |
| 音声ファイルとして残したい | `speak 原稿.ssml --output 出力.wav` | 手順は次の節 |
| 原稿の区切りだけ確かめたい | `plan 原稿.ssml` | モデルを使わず、すぐ終わる |
| 声を増やす・確かめる・作り直す・消す | `voice add` / `voice list` / `voice build` / `voice remove` | 手順は「声を登録する」 |
| エンジンを入れる・確かめる | `engine install` / `engine list` | |
| 他のアプリから呼びたい | `api` | 手順は「OpenAI互換API」 |
| サーバーの様子を見る・止める | `server status` / `server stop` | |

`say`は毎回スピーカーから音が出る。納品するファイルや、音を出さずに作りたいときは`speak`を使う。
このMacでは、どのエンジンも生成が実時間より遅い。`say`は文を作り終えてから（VoxCPM2とS2は一部を溜めてから）話すので、話し出すまで数秒から十数秒かかる。

声は設定の既定の声を使う。別の声なら`--voice <名前>`を付け、候補は`voice list`で確かめる。

## 4. 文章をWAVにする

`speak`の入力はSSMLなので、文章を次の形のファイルに書く。

```xml
<?xml version="1.0" encoding="UTF-8"?>
<speak xmlns="http://www.w3.org/2001/10/synthesis" version="1.1" xml:lang="ja-JP">
  <s>一文ずつ、この要素に入れます。</s>
  <break time="500ms"/>
  <s>間が欲しい位置には、break を置きます。</s>
</speak>
```

- 1発話は300文字まで、入力全体は128KBまで。長い文章は句点で`<s>`に分ける。
- 文章に`&`や`<`が含まれていたら、XMLとして`&amp;`・`&lt;`にエスケープする。
- 対応する要素は`s`、`p`、`break`、`prosody`、`sub`、`emphasis`、`mark`だけ。`say-as`や`phoneme`、`voice`は合成の前にエラーになる（[対応範囲](references/engine.md)）。

まず`plan`で区切りを確かめ、次に合成する。

```console
uv run --project "<local-tts>/tools" local-tts plan "原稿.ssml"
uv run --project "<local-tts>/tools" local-tts speak "原稿.ssml" --output "出力.wav" --voice <名前>
uv run --project "<local-tts>/tools" local-tts speak "原稿.ssml" --output "出力.wav" --engine voxcpm2
```

- 既定の出力は`outputs/presentation.wav`。同名のJSONに区間ごとの時間が残る。
- 既存の出力は上書きしない。作り直すと確認できたときだけ`--force`を付ける。
- 生成は実時間より遅い。このMac（M4）でOmniVoice・VoxCPM2は音声の約1.9倍、S2は約7〜11倍、RTX 3080のS2は約1.4倍（各実測）。初回はモデルの読み込みに20〜30秒かかる。1分を超えそうな音声は、**目安の時間を伝えてからバックグラウンドで実行する**。
- OmniVoiceは、`break`や`mark`で区切られていない文を200文字までまとめて1回で生成する（1回ごとの固定の時間が大きいため）。その場合、時間のJSONの区間もまとめた単位になる。
- 1本の音声の中でエンジンを混ぜない。続きを作り直すときは、前と同じ`--engine`を付ける。

### 読み間違いを減らす表記

モデルは表記から読みを推測するので、英字、数字、記号で誤りやすい。読ませたい形で書く。

| 元の表記 | 書き換え |
|---|---|
| `goroutine`、`API`などの英字 | `ゴルーチン`、`エーピーアイ`。SSMLでは`<sub alias="ゴルーチン">goroutine</sub>`も使える |
| `100,000個`、`48ms` | `十万個`、`四十八ミリ秒` |
| `A/B`、`→`などの記号 | `エービー`のように読みを書くか、言葉に置き換える |

これは誤読を減らすための方針で、正しく読めたことの保証にはならない。確かめられるのは実際に聞いたときだけである。

## 5. 声を登録する

```console
uv run --project "<local-tts>/tools" local-tts voice add <名前> "<録音>" --text "<録音で話している内容>"
uv run --project "<local-tts>/tools" local-tts voice list
```

- **本人の声か、本人の許可を得た声だけを登録する。** 声は本人を特定でき、なりすましにも使える。許可が分からない他人の声（配信の切り抜きなど）は、登録する前に確認する。
- 録音は5〜30秒で、BGMや他人の声が入っていない区間にする。長い録音は話している区間を切り出し、候補をユーザーに聞いてもらって選ぶ。
- 文字起こしは録音とそのまま一致させる。ずれると声の再現が悪くなるので、分からない部分を推測で埋めない。ユーザーに書き起こしてもらうか、聞き取れた範囲だけにする。
- 声の本体は録音と文字起こし（`<home>/voices/`）で、どのエンジンでも使える。エンジンごとのプロファイルは`<home>/cache/voices/<エンジン>/`に置く。S2のものは、S2が入っていれば登録のときに作る。OmniVoice・VoxCPM2のものは、初めて使うときに作る。消えていても、使うときに録音から作り直す（S2は約1分）。
- `voice list`の`[ ]`は、プロファイルを作り終えたエンジン。作り直しは`voice build <名前> --engine <エンジン>`。
- 作り直しは`--force`。失敗しても前の声は残る。登録し直すと、各エンジンのプロファイルも作り直される。
- 声の削除（`voice remove`）は取り消せず、録音からの登録し直しになる。ユーザーが名前で指定したときだけ実行する。

既定の声にするときは`<home>/config.toml`の先頭の`voice = "<名前>"`を有効にする。

## 6. OpenAI互換API

他のアプリやプログラムから、OpenAIの音声API（`POST /v1/audio/speech`）と同じ形式で呼び出すためのサーバーを立てる。リクエストの`model`で`omnivoice`・`voxcpm2`・`s2-pro`を選べる（`tts-1`などは既定のエンジン）。

このコマンドは**既定で`0.0.0.0:8000`に公開する**。同じネットワークの機器から、APIキーを知っている人が登録済みの声で何でも話させられる。
そのため、次のように扱う。

- 他の機器から使うと言われていなければ、`--host 127.0.0.1`を付けて自分のPCだけに閉じる（この場合はキーが不要になる）。

  ```console
  uv run --project "<local-tts>/tools" local-tts api --host 127.0.0.1 --voice <名前>
  ```

- 他の機器へ公開するのは、ユーザーが求めたときだけにし、信頼できるプライベートネットワークであることを確かめる。
- APIキーは起動時の表示と`<home>/api-key.txt`にある。ユーザーが必要とするとき以外は、報告やファイルに書き写さない。
- 止めるまで動き続けるので**バックグラウンドで実行し**、用が済んだら止める。エンジンのサーバーは別に動き続けるので、`server stop`も行う。

リクエストの項目や呼び出し例は[コマンド一覧](references/commands.md)にある。

## 7. 渡すときの報告

ファイルの場所、合計の長さ、使った声と**エンジン**、**聞いて確かめた範囲とまだ聞いていない範囲**を伝える。
音声を聞く手段がないときは、ユーザーに試聴してもらう箇所（数字、英字、固有名詞、長い文）を具体的に挙げる。長さや音量の確認を、聞いて確かめたことの代わりにしない。

読み間違いがあれば、原稿の表記を直して作り直す。

## 気をつけること

- 使い終わったらエンジンのサーバーを止める（`server stop`）。動いている間はメモリを使う（OmniVoice約4 GB、VoxCPM2約14 GB、S2約4 GB。Macはユニファイドメモリ）。ユーザーが続けて使う場合は残してよい。
- WindowsのCUDAでは、空きVRAMが足りないエンジンは起動を止める。他のエンジンを`server stop`で止めてから使う。
- S2（s2.cppとS2 Proのモデル）は**Fish Audio Research License**で、研究・非商用の利用は無償、**商用利用にはFish Audioとの別途の契約が必要**。業務や収益化に使うと分かったら伝える。OmniVoiceとVoxCPM2はApache-2.0だが、なりすまし・詐欺・偽情報への使用は禁じられている。
- 合成した声を公開・配布する場合は、合成音声であることを示すかどうかをユーザーに確かめる。
- 生成に失敗したときは、エラーの1行目と`<home>/cache/<エンジン>-server.log`（S2は`s2-server.log`）の末尾を読んでから対処する。原因が分からないまま再試行を繰り返さない。
- ディスクを空けたい、作り直したい、消したいと言われたら[片付け手順](references/cleanup.md)に従う。声・設定・APIキーは取り直せないので、消す前に必ず確認する。

## 同梱物

| パス | 中身 | 読むとき |
|---|---|---|
| `references/commands.md` | 全コマンド、APIの項目と例、設定、移し替え、症状別の対処 | オプションや設定、不調を扱うとき |
| `references/engines.md` | 3つのエンジンの計測値、仕組み、Windowsでの確認手順 | エンジンを選ぶ、速度やメモリの問題、Windowsで確かめるとき |
| `references/engine.md` | SSMLの対応範囲、S2（s2.cpp）の仕組みと検証結果 | SSMLの詳細やS2の問題を扱うとき |
| `references/setup.md` | 前提ソフト、エンジンの導入、S2のライセンス確認とビルド | エンジンが`ready`でない、ビルドし直すとき |
| `references/cuda-wsl.md` | WindowsのCUDAとWSLの確認 | WindowsのCUDAで問題が出たとき |
| `references/cleanup.md` | ローカルデータの片付け | 片付け、アンインストール |
| `references/upstream.md` | presenterから切り出して分けた経緯と、修正の取り込み方 | このスキル自体を更新するとき |
| `tools/` | local-tts本体、テスト、`local-tts.example.toml` | 実行、改修 |
| `tools/engines/` | OmniVoice・VoxCPM2のサーバーと、固定した依存関係（`uv.lock`） | エンジンを改修・更新するとき |
