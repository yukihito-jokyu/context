# local-tts のコマンド

`<local-tts>`はこのスキルのフォルダ。`<home>`はWindowsでは`%LOCALAPPDATA%\local-tts`、Macでは`~/.local/share/local-tts`（環境変数`LOCAL_TTS_HOME`で変更可）。
エンジンやモデルの準備は[セットアップ手順](setup.md)で行う。エンジンの選び方と仕組みは[engines.md](engines.md)、SSMLとS2の詳細は[engine.md](engine.md)にある。`<home>`はpresenterスキルとは共有しない。

## 0. 呼び方

すべて`uv run --project "<local-tts>/tools" local-tts ...`で呼ぶ。どのフォルダから実行してもよい。
初回の呼び出しで、uvが`<local-tts>/tools/.venv`にPython 3.11とTyperを`uv.lock`のとおり入れる。`uv sync`は不要。
設定は`<home>/config.toml`（なければ既定値）。別の設定を使うときは`--config <file>`をコマンド名の直後に付ける。

| 場所 | 中身 | 消してよいか |
|---|---|---|
| `<home>/cache/` | エンジンの実行環境（`engines/`）、モデル（`huggingface/`、`models/`）、s2.cppとビルド、エンジン別の声のプロファイル（`voices/`）、ログ、フィラー | よい（[セットアップ手順](setup.md)で取り直せる） |
| `<home>/voices/` | 登録した声と元の録音 | 消さない（取り直せない） |
| `<home>/config.toml`、`<home>/api-key.txt` | 設定とAPIキー | 消さない |

片付けの手順は[cleanup.md](cleanup.md)。

## 1. エンジンのサーバー

`say`・`speak`・`api`は、選んだエンジンのサーバーに音声を作らせる（`--engine`、なければ設定の`engine`、なければVoxCPM2）。

```console
uv run --project "<local-tts>/tools" local-tts server start --engine omnivoice
uv run --project "<local-tts>/tools" local-tts server status
uv run --project "<local-tts>/tools" local-tts server stop
uv run --project "<local-tts>/tools" local-tts server stop --engine voxcpm2
```

- `start`はサーバーを裏で（別プロセスで）起動し、リクエストを受け付けられるまで待ってから戻る。ターミナルを閉じても動き続ける。
- `say`・`speak`・`api`は、サーバーが止まっていれば自動で起動する。自動起動しない場合は、S2は`[server] auto_start = false`、PyTorchのエンジンは`[engines.<名前>] auto_start = false`。
- 動いている間のメモリはOmniVoice約4 GB、VoxCPM2約14 GB（CUDAは約8 GB）、S2約4.6 GB。使い終わったら`stop`で止める。`stop`は止まりきるまで待ってから戻る。
- `status`は全エンジンを表示する（`--engine`で1つだけ）。`stop`は`--engine`がなければ、このツールが起動したサーバーをすべて止める。手動で起動したサーバーは、そのターミナルでCtrl+Cを押して止める。
- WindowsのCUDAで空きVRAMが目安より少ないと、PyTorchのエンジンは起動を止める。動いているエンジンを`stop`してから使う。
- S2のGPUに載せる層の数やコーデックの置き場所は、設定の`[server]`（`gpu_layers`、`codec_gpu`）で変える。
- `[server] parallel`はS2のサーバーを複数立てる設定だが、`say`・`speak`・`api`は1台目のサーバーしか使わない。2以上だと使わないサーバーの分だけメモリを消費するので、1のままにする。
- 起動時の出力は`<home>/cache/<エンジン>-server.log`（S2は`s2-server.log`）に残る。起動に失敗したときは、このログの末尾も表示する。

## 2. 話させる（say）

```console
uv run --project "<local-tts>/tools" local-tts say
```

`> `が出たら文字を入力してEnter。生成しながら再生する。

| 入力 | 動作 |
|---|---|
| 文章 | 読み上げる。最後の音声は`outputs/say.wav`に保存 |
| `/voice 名前` | 声を切り替える（`/voice default`で標準の声） |
| Ctrl+C | 終了 |

1回だけ話させる、声を指定する場合:

```console
uv run --project "<local-tts>/tools" local-tts say こんにちは、テストです。
uv run --project "<local-tts>/tools" local-tts say --voice myvoice
```

長い文は「、」で区切って少しずつ生成する（区切りの間に短い間が入る）。OmniVoiceは1回ごとの固定の時間が大きいので、区切らずに200文字までまとめて生成する。本文がなかなか届かないときは、その声とエンジンの「えーと」などのフィラーが入ることがある。

## 3. 声を登録する（voice）

録音と、その録音で話している内容をそのまま書いた文字起こしから、声を作る。

```console
uv run --project "<local-tts>/tools" local-tts voice add myvoice 録音.wav --text "録音で話している内容"
uv run --project "<local-tts>/tools" local-tts voice list
uv run --project "<local-tts>/tools" local-tts voice build myvoice --engine voxcpm2
uv run --project "<local-tts>/tools" local-tts voice remove myvoice
```

- 使ってよい声（自分の声、または本人の許可を得た声）だけを登録する。
- 録音は5〜30秒、ピアノやBGM、ほかの人の声が入っていない区間がよい。長い録音は、話している区間だけを切り出してから使う。
- 小さい録音は自動で音量を上げてから登録する（`--no-boost`で無効）。
- 声の本体は録音（`<名前>.wav`）と文字起こし（`<名前>.json`）で、どのエンジンでも使う。S2が入っていれば、S2用のプロファイル（`<home>/cache/voices/s2/<名前>.s2voice`）もCPUで作る（約30秒〜1分。サーバーを止めているときは`--gpu`で速くできる）。消えていれば、S2で使うときに録音から作り直す。2026-11-11より前に`voices/`へ置かれた`.s2voice`は、次のコマンドの実行時にここへ移る（録音のない古い声は`voices/`に残す）。
- OmniVoice・VoxCPM2のプロファイルは、初めて使うときに作って`<home>/cache/voices/<エンジン>/`に残す。録音を作り直すと、自動で作り直される。
- 作成後、確認用の文を選んだエンジン（`--engine`）で`outputs/voice-<名前>.wav`に作って再生する（`--no-preview`で再生しない）。
- `voice build`は、保存してある録音から1つのエンジンのプロファイルを作り直す。
- `voice list`の`[s2,omnivoice]`のような印は、プロファイルを作り終えたエンジン。
- `voice list`の`*`は、`--voice`を付けないときに使う声（設定の`voice = "名前"`）。
- 声は`<home>/voices/`に入り、どのプロジェクトからも名前で使える（元の録音は`<home>/voices/sources/`に置くとよい）。
  `<home>/cache/`とは分けてあるので、容量を空けるために`cache/`を消しても声は残る。

| オプション | 意味 |
|---|---|
| `--text`、`-t` | 文字起こし |
| `--text-file` | 文字起こしをファイルから読む |
| `--force` | 同じ名前の声を作り直す |
| `--sample` | 確認用に話させる文 |
| `--engine` | 確認用の文を作るエンジン。`s2`ならS2のプロファイルが必須になる |

## 4. 発表原稿を読み上げる（speak、plan）

SSMLで書いた原稿をWAVにする。

```console
uv run --project "<local-tts>/tools" local-tts plan "<local-tts>/tools/examples/presentation.ssml"
uv run --project "<local-tts>/tools" local-tts speak "<local-tts>/tools/examples/presentation.ssml" --force
uv run --project "<local-tts>/tools" local-tts speak "<local-tts>/tools/examples/presentation.ssml" --voice myvoice --play --force
```

- `plan`はモデルを使わず、区切り・間・マーカーをJSONで表示する。原稿の確認用。
- `speak`は`outputs/presentation.wav`に保存する（`--output`で変更）。同名のJSONに区間ごとの時間も保存する。
- `--play`は生成しながら再生する。生成が再生より遅いため、途中で途切れることがある。
- 既存の出力は`--force`を付けない限り上書きしない。

## 5. OpenAI互換のAPI（api）

OpenAIの音声合成API（`POST /v1/audio/speech`）と同じ形で使えるサーバーを立てる。
OpenAIのSDKや、OpenAI互換のTTSに対応したアプリから、接続先を変えるだけで使える。

```console
uv run --project "<local-tts>/tools" local-tts api --voice myvoice
```

起動すると、接続先とAPIキーを表示する。Ctrl+Cで止まる。TTSサーバーが止まっていれば自動で起動する。

```
OpenAI-compatible speech API: http://localhost:8000/v1 (Ctrl+C stops)
Listening on 0.0.0.0: other devices use this PC's IP address.
API key: ...
```

- 既定では`0.0.0.0:8000`で待ち受け、同じネットワークのほかの機器（スマホ、別のPC）からも使える。ほかの機器からは`http://<このPCのIPアドレス>:8000/v1`へ接続する。OSのファイアウォール確認が出たら、信頼できるプライベートネットワークだけを許可する。
- ネットワークに公開すると、だれでもクローンした声で話させられてしまうため、APIキーが必須。キーは初回に作って`<home>/api-key.txt`に保存し、以降も同じものを使う。自分で決める場合は`--api-key`か環境変数`LOCAL_TTS_API_KEY`。
- このPCだけで使うなら`--host 127.0.0.1`。この場合はキーが不要になる。
- `--port`で待ち受けるポートを変えられる。

リクエストの項目:

| 項目 | 内容 |
|---|---|
| `input` | 読み上げる文章（4096文字まで） |
| `voice` | 登録した声の名前（`myvoice`など）。`alloy`などOpenAIの声の名前や省略時は`--voice`の声 |
| `response_format` | `mp3`（既定）、`opus`、`aac`、`flac`、`wav`、`pcm`（24 kHz・16ビット・モノラル） |
| `speed` | 話す速さ（0.25〜4.0、既定1.0） |
| `model` | エンジン。`omnivoice`、`voxcpm2`、`s2-pro`、`voicevox`。`tts-1`などOpenAIの名前や省略時は`api --engine`か設定の`engine`。止まっていれば自動で起動する |

音声は生成しながら返す（ストリーミング）。s2.cppは一度に1件しか処理できないため、同時に来たリクエストは順番に処理する。

PowerShellから試す例（`<APIキー>`は起動時に表示されたもの）:

```powershell
$body = @{ model = "tts-1"; input = "こんにちは。"; voice = "myvoice" } | ConvertTo-Json
Invoke-WebRequest http://localhost:8000/v1/audio/speech -Method Post -Headers @{ Authorization = "Bearer <APIキー>" } -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($body)) -OutFile hello.mp3
```

Macのシェルから試す例:

```bash
curl http://localhost:8000/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <APIキー>' \
  -d '{"model":"tts-1","input":"こんにちは。","voice":"myvoice"}' \
  --output hello.mp3
```

OpenAIのPython SDKから使う例:

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="<APIキー>")
with client.audio.speech.with_streaming_response.create(
        model="tts-1", voice="myvoice", input="こんにちは。") as response:
    response.stream_to_file("hello.mp3")
```

## 6. 調子が悪いとき（doctor）

```console
uv run --project "<local-tts>/tools" local-tts doctor
```

OS、CPUアーキテクチャ、CUDA/Metal、FFmpeg/FFplay（Macは再生用の`swiftc`も）、ネットワーク、サーバーのポートをまとめて確認する。

| 症状 | 確認すること |
|---|---|
| `Cannot reach http://127.0.0.1:303x` | `server status`。止まっていれば`server start --engine <名前>` |
| `... is not installed; run: local-tts engine install ...` | そのエンジンが未導入。[セットアップ手順](setup.md)で承認を得てから入れる |
| `Voices and settings are still in the old folder` | 旧presenter-ttsフォルダから移していない。8節の`home migrate` |
| `has no S2 profile yet` | S2がない環境で登録した声。`voice build <名前> --engine s2` |
| 再生がプツプツする | 設定の`stream_start_buffer_ms_per_char`を上げる |
| クローンした声が小さい | 録音の音量。`voice add --force`で作り直す |
| 声が似ていない | 録音を長くする（10秒以上）、文字起こしが録音と合っているか確認 |
| サーバーが起動しない | `<home>/cache/<エンジン>-server.log`の末尾。S2でGPUメモリ不足なら`[server] gpu_layers`を下げる。PyTorchのエンジンは他のエンジンを止める |
| APIが`401`を返す | `Authorization: Bearer <APIキー>`。キーは`<home>/api-key.txt` |
| ほかの機器からAPIにつながらない | OSのファイアウォールでPythonを許可しているか、IPアドレスが合っているか |

## 7. 設定（<home>/config.toml）

| 場所 | 項目 | 意味 |
|---|---|---|
| 先頭 | `engine` | 既定のエンジン（`voxcpm2`、`omnivoice`、`s2`、`voicevox`）。省略時はVoxCPM2。古い`backend = "s2cpp"`は`s2`として読む |
| 先頭 | `url` | S2（s2.cpp）のアドレス（既定`http://127.0.0.1:3030`） |
| 先頭 | `voice` | 普段使う声の名前（`voice list`の名前）か`.s2voice`のパス |
| `[engines.omnivoice]` | `language` | 言語名（`Japanese`など）。指定すると少し良くなる（README）。混在する文章では外す |
| `[engines.omnivoice]` | `num_step`、`guidance_scale` | 拡散のステップ数（既定32。16で約2倍速いが質は未確認）、ガイダンス（既定2.0） |
| `[engines.omnivoice]` | `request_chars` | 1回にまとめて送る文字数（既定200、0で文ごと） |
| `[engines.voxcpm2]` | `cfg_value`、`inference_timesteps` | ガイダンス（既定2.0）、拡散のステップ数（既定10） |
| `[engines.voxcpm2]` | `stream_start_buffer_ms_per_char` | 生成しながら再生するとき、1文字あたり先に溜める時間（Mac既定120、ほか0） |
| `[engines.<名前>]` | `url`、`device`、`dtype`、`timeout`、`auto_start` | アドレス、`auto`（CUDA→MPS→CPU）か`cuda`・`mps`・`cpu`、OmniVoiceの精度（GPUは既定`float16`）、1リクエストの待ち時間（既定600秒）、自動起動 |
| `[engines.voicevox]` | `url` | VOICEVOX ENGINEのアドレス（既定`http://127.0.0.1:50021`）。話者は先頭の`speaker` |
| `[generation]` | `stream_start_buffer_ms_per_char` | 話し始める前に、1文字あたりためる時間（途切れ対策） |
| `[server]` | `auto_start` | `say`/`speak`でサーバーを自動起動するか（既定true） |
| `[server]` | `accelerator` | `auto`ならWindowsでCUDA、MacでMetal。明示値は`cuda`、`metal`、`cpu` |
| `[server]` | `gpu_device` | CUDAのデバイス番号（既定0。Metalでは使わない） |
| `[server]` | `gpu_layers` | GPUに載せる層の数（既定36＝全部） |
| `[server]` | `codec_gpu` | CUDAで音声コーデックもGPUへ載せるか（既定true）。Metalは未対応のPAD演算があるため常にCPU |
| `[server]` | `threads` | サーバー1台が使うCPUスレッド数（既定0＝自動。Macは高性能コアの数、Windowsはs2.cppが決める） |
| `[server]` | `parallel` | 立てるサーバーの数（既定1）。このスキルでは1のままにする |
| `[say]` | `filler` | フィラーを使うか |
| `[say]` | `filler_after_ms` | 本文がこの時間までに届かなければフィラーを流す |
| `[say]` | `filler_probability` | フィラーを流す確率 |
| `[say]` | `max_chars` | 長い文を区切る目安の文字数 |
| `[say]` | `split_first_clause` | 最初の文を「、」で分けて話し始めを早くするか |

すべてのオプションは`--help`で確認できる。

```console
uv run --project "<local-tts>/tools" local-tts --help
uv run --project "<local-tts>/tools" local-tts voice add --help
```

## 8. データのフォルダ（home）

2026-11-11に、データのフォルダを`presenter-tts`から`local-tts`に変えた。旧フォルダにだけ声や設定があると、`doctor`・`plan`・`home`以外のコマンドは止まって案内する。

```console
uv run --project "<local-tts>/tools" local-tts home show
uv run --project "<local-tts>/tools" local-tts home migrate --dry-run
uv run --project "<local-tts>/tools" local-tts home migrate
```

- `--dry-run`は、コピーするもの・移動するもの・大きさを表示するだけで、何も変えない。**声を扱うので、この結果を見せて承認を得てから本番を実行する。**
- 声（`voices/`）、`config.toml`とそのバックアップ、`api-key.txt`は**コピー**する。旧フォルダにも残る（新しいフォルダに同じ名前があれば上書きしない）。
- `cache/`（S2のモデル、s2.cppのソース、フィラー、ログ）は**移動**する。動いているサーバーがあれば止めるよう求める。
- Macのs2.cppのビルド（`cache/s2-build`）は、ライブラリを絶対パスで参照しているので移さない。移したあとに`tools/scripts/setup-s2.sh`でビルドし直す（モデルは照合だけで、ダウンロードし直さない）。Windowsのビルドは移し、CMakeのキャッシュだけ消す。
- ユーザーのHugging Faceのキャッシュ（`~/.cache/huggingface/hub`）にOmniVoice・VoxCPM2のモデルがあれば、`<home>/cache/huggingface/hub/`へ移動する。
- 旧フォルダには`MOVED-TO-local-tts.txt`を置く。旧フォルダを消すかどうかは、presenterや古い版のremote-ttsを使い続けるかを確かめてから決める。
- 環境変数は`LOCAL_TTS_HOME`・`LOCAL_TTS_API_KEY`。旧名の`PRESENTER_TTS_HOME`・`PRESENTER_TTS_API_KEY`も警告付きで読む。

## 9. エンジン（engine）

```console
uv run --project "<local-tts>/tools" local-tts engine list
uv run --project "<local-tts>/tools" local-tts engine install omnivoice
uv run --project "<local-tts>/tools" local-tts engine install voxcpm2
```

- `list`は、各エンジンが使える状態か、アドレス、ライセンスを表示する。`*`は既定のエンジン。
- `install`は、`tools/engines/<名前>/uv.lock`のとおりに実行環境を`<home>/cache/engines/<名前>/.venv`へ入れ、モデルを`<home>/cache/huggingface/`へダウンロードする（既にあれば照合だけ）。WindowsはCUDA 12.8版、MacはMPS対応のPyTorchが入る。
- S2は`install`ではなく、[セットアップ手順](setup.md)でビルドする。
