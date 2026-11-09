---
name: local-tts
description: スライドや検査済み原稿を伴わない、ローカルのFish Audio S2 Pro（s2.cpp）の音声合成を運用する。文章をその場で読み上げる、テキストやSSMLをWAVにする、録音から声をクローンして登録・一覧・削除する、TTSサーバーを起動・停止する、OpenAI互換の音声API（/v1/audio/speech）を立てる、不調を切り分ける、エンジンのビルドとモデル取得、キャッシュの片付けに使う。「読み上げて」「音声にして」「WAVにして」「この声で話して」「声を登録して」「TTSサーバーを止めて」「ローカルTTS」「音声APIを立てて」では、スキル名を言われなくてもこのスキルを使う。html-deckのスライドにナレーションを付ける、player.htmlやMP4を作る場合はpresenter、発表原稿の作成や検査はpresentation-jaを使う。
license: MIT
compatibility: Windows 10/11＋NVIDIA GPU/CUDA 12.4以上、またはApple Silicon Mac＋Metalに対応。uv、FFmpegが必要。初回のビルドにはGit、CMake、WindowsはVisual Studio C++、MacはXcode Command Line Tools、GitHub/Hugging Face接続が必要。
---

# local-tts

ローカルのFish Audio S2 Proで、文章を声にする。外部のAPIには送らない。

コードは同梱の`tools/`（uvのプロジェクト、パッケージ名`presenter_tts`）にある。
`<local-tts>`をこのSKILL.mdのあるフォルダとして、すべて次の形で呼ぶ。パスに空白が入ることがあるので引用符で囲む。

```console
uv run --project "<local-tts>/tools" presenter-tts <command> ...
```

初回の呼び出しでuvが依存関係をそろえるので、`uv sync`は不要。

エンジン、モデル、声、設定は`<home>`（Macは`~/.local/share/presenter-tts`、Windowsは`%LOCALAPPDATA%\presenter-tts`、`PRESENTER_TTS_HOME`で変更可）にあり、presenterスキルと共有している。
そのためpresenterで登録した声はここでも使える。逆に`<home>`の中を消すとpresenterも影響を受ける。

## 1. 動く状態か確かめる

```console
uv run --project "<local-tts>/tools" presenter-tts doctor
```

`engine.ready`がfalseなら、[セットアップ手順](references/setup.md)に従う。ライセンスへの同意とソフトの導入の承認が必要なので、勝手に進めない。
TTSサーバーは`say`・`speak`・`api`が自動で起動するので、手動で起動しなくてよい。

## 2. 目的からコマンドを選ぶ

| 目的 | コマンド | 補足 |
|---|---|---|
| いま声で聞きたい | `say "文章"` | 生成しながらスピーカーで再生する。`outputs/say.wav`にも残る |
| 音声ファイルとして残したい | `speak 原稿.ssml --output 出力.wav` | 手順は次の節 |
| 原稿の区切りだけ確かめたい | `plan 原稿.ssml` | モデルを使わず、すぐ終わる |
| 声を増やす・確かめる・消す | `voice add` / `voice list` / `voice remove` | 手順は「声を登録する」 |
| 他のアプリから呼びたい | `api` | 手順は「OpenAI互換API」 |
| サーバーの様子を見る・止める | `server status` / `server stop` | |

`say`は、音声の到着が遅いと「えーと」などのフィラーを再生に挟むことがある。また、毎回スピーカーから音が出る。
納品するファイルや、音を出さずに作りたいときは`speak`を使う。

声は設定の既定の声を使う。別の声なら`--voice <名前>`を付け、候補は`voice list`で確かめる。

## 3. 文章をWAVにする

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
uv run --project "<local-tts>/tools" presenter-tts plan "原稿.ssml"
uv run --project "<local-tts>/tools" presenter-tts speak "原稿.ssml" --output "出力.wav" --voice <名前>
```

- 既定の出力は`outputs/presentation.wav`。同名のJSONに区間ごとの時間が残る。
- 既存の出力は上書きしない。作り直すと確認できたときだけ`--force`を付ける。
- 生成は実時間より遅い。Macでは音声の長さの約7〜11倍、RTX 3080では約1.4倍かかる（M5とM4、RTX 3080での実測）。1分を超えそうな音声は、**目安の時間を伝えてからバックグラウンドで実行する**。

### 読み間違いを減らす表記

モデルは表記から読みを推測するので、英字、数字、記号で誤りやすい。読ませたい形で書く。

| 元の表記 | 書き換え |
|---|---|
| `goroutine`、`API`などの英字 | `ゴルーチン`、`エーピーアイ`。SSMLでは`<sub alias="ゴルーチン">goroutine</sub>`も使える |
| `100,000個`、`48ms` | `十万個`、`四十八ミリ秒` |
| `A/B`、`→`などの記号 | `エービー`のように読みを書くか、言葉に置き換える |

これは誤読を減らすための方針で、正しく読めたことの保証にはならない。確かめられるのは実際に聞いたときだけである。

## 4. 声を登録する

```console
uv run --project "<local-tts>/tools" presenter-tts voice add <名前> "<録音>" --text "<録音で話している内容>"
uv run --project "<local-tts>/tools" presenter-tts voice list
```

- **本人の声か、本人の許可を得た声だけを登録する。** 声は本人を特定でき、なりすましにも使える。許可が分からない他人の声（配信の切り抜きなど）は、登録する前に確認する。
- 録音は5〜30秒で、BGMや他人の声が入っていない区間にする。長い録音は話している区間を切り出し、候補をユーザーに聞いてもらって選ぶ。
- 文字起こしは録音とそのまま一致させる。ずれると声の再現が悪くなるので、分からない部分を推測で埋めない。ユーザーに書き起こしてもらうか、聞き取れた範囲だけにする。
- 作り直しは`--force`。失敗しても前の声は残る。
- 声の削除（`voice remove`）は取り消せず、録音からの登録し直しになる。ユーザーが名前で指定したときだけ実行する。

既定の声にするときは`<home>/config.toml`の先頭の`voice = "<名前>"`を有効にする。

## 5. OpenAI互換API

他のアプリやプログラムから、OpenAIの音声API（`POST /v1/audio/speech`）と同じ形式で呼び出すためのサーバーを立てる。

このコマンドは**既定で`0.0.0.0:8000`に公開する**。同じネットワークの機器から、APIキーを知っている人が登録済みの声で何でも話させられる。
そのため、次のように扱う。

- 他の機器から使うと言われていなければ、`--host 127.0.0.1`を付けて自分のPCだけに閉じる（この場合はキーが不要になる）。

  ```console
  uv run --project "<local-tts>/tools" presenter-tts api --host 127.0.0.1 --voice <名前>
  ```

- 他の機器へ公開するのは、ユーザーが求めたときだけにし、信頼できるプライベートネットワークであることを確かめる。
- APIキーは起動時の表示と`<home>/api-key.txt`にある。ユーザーが必要とするとき以外は、報告やファイルに書き写さない。
- 止めるまで動き続けるので**バックグラウンドで実行し**、用が済んだら止める。

リクエストの項目や呼び出し例は[コマンド一覧](references/commands.md)にある。

## 6. 渡すときの報告

ファイルの場所、合計の長さ、使った声、**聞いて確かめた範囲とまだ聞いていない範囲**を伝える。
音声を聞く手段がないときは、ユーザーに試聴してもらう箇所（数字、英字、固有名詞、長い文）を具体的に挙げる。長さや音量の確認を、聞いて確かめたことの代わりにしない。

読み間違いがあれば、原稿の表記を直して作り直す。

## 気をつけること

- 使い終わったらTTSサーバーを止める（`server stop`）。動いている間はGPUメモリ（Macではユニファイドメモリ）を約4 GB使う。ユーザーが続けて使う場合は残してよい。
- s2.cppとS2 Proのモデルは**Fish Audio Research License**で、研究・非商用の利用は無償、**商用利用にはFish Audioとの別途の契約が必要**。業務や収益化に使うと分かったら伝える。
- 合成した声を公開・配布する場合は、合成音声であることを示すかどうかをユーザーに確かめる。
- 生成に失敗したときは、エラーの1行目と`<home>/cache/s2-server.log`の末尾を読んでから対処する。原因が分からないまま再試行を繰り返さない。
- ディスクを空けたい、作り直したい、消したいと言われたら[片付け手順](references/cleanup.md)に従う。声・設定・APIキーは取り直せず、presenterとも共有しているので、消す前に必ず確認する。

## 同梱物

| パス | 中身 | 読むとき |
|---|---|---|
| `references/commands.md` | 全コマンド、APIの項目と例、設定、症状別の対処 | オプションや設定、不調を扱うとき |
| `references/engine.md` | SSMLの対応範囲、エンジンの仕組み、検証結果 | SSMLの詳細や速度の問題を扱うとき |
| `references/setup.md` | 前提ソフト、ライセンス確認、ビルド、モデル取得 | `engine.ready`がfalse、ビルドし直すとき |
| `references/cuda-wsl.md` | WindowsのCUDAとWSLの確認 | WindowsのCUDAで問題が出たとき |
| `references/cleanup.md` | ローカルデータの片付け | 片付け、アンインストール |
| `references/upstream.md` | presenterから切り出した範囲と、修正の取り込み方 | このスキル自体を更新するとき |
| `tools/` | presenter-tts本体、テスト、`presenter.example.toml` | 実行、改修 |
