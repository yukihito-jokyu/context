# エンジンの詳細（OmniVoice、VoxCPM2、S2）

`<local-tts>`はこのスキルのフォルダ、`<home>`はデータのフォルダ（Macは`~/.local/share/local-tts`、Windowsは`%LOCALAPPDATA%\local-tts`）。
S2（s2.cpp）の仕組みと検証結果は[engine.md](engine.md)にある。

## 仕組み

```
local-tts（制御側：Typerだけ。PyTorchを読み込まない）
  ├─ omnivoice → tools/engines/omnivoice/server.py  :3032  <home>/cache/engines/omnivoice/.venv
  ├─ voxcpm2   → tools/engines/voxcpm2/server.py    :3031  <home>/cache/engines/voxcpm2/.venv
  ├─ s2        → s2.cpp                             :3030  <home>/cache/s2-build
  └─ voicevox  → ユーザーが起動するVOICEVOX ENGINE    :50021
```

- どのエンジンのサーバーも、s2.cppと同じ`POST /generate`（multipartで`text`・`params`・`voice`を受け、PCM16に`X-Audio-Encoding`・`X-Audio-Sample-Rate`・`X-Audio-Channels`を付けて返す）に応じる。そのため`say`・`speak`・`api`、話速・音量・ピッチ（FFmpeg）、マーカーの時刻は、エンジンによらず同じ処理を通る。
- PyTorchのエンジンは`127.0.0.1`だけで待ち受け、`HF_HUB_OFFLINE=1`で動く。モデルは`<home>/cache/huggingface/`にあり、実行中に外部へ通信しない。
- 1台のサーバーは1件ずつ生成する。重なったリクエストは順番を待つ。
- 実行環境はエンジンごとに分ける。PyTorchとtransformersの必要な版が違うため（OmniVoiceはtransformers 5.3以上、VoxCPMは検証した版で5.22）。

## 声のプロファイル

- 声の本体は`<home>/voices/<名前>.wav`（44.1 kHz・PCM16・ピーク-3 dB）と`.json`（文字起こし）。
- OmniVoiceとVoxCPM2は、初めてその声を使うときにプロファイルを作り、`<home>/cache/voices/<エンジン>/<名前>.pt`に保存する。録音と文字起こしのSHA-256を一緒に残し、録音が変わったら作り直す。2回目からは保存したものを読み込む。
  - OmniVoice: 公式の`create_voice_clone_prompt`→`VoiceClonePrompt.save/load`。作成は約3秒。
  - VoxCPM2: モデルカードの「Ultimate Cloning」と同じく、同じ録音を続き生成の手本（文字起こし付き）と話者の参照の両方に使う。`build_prompt_cache`の結果を保存し、`_generate_with_prompt_cache`（`VoxCPM.generate`が内部で呼ぶもの）で使う。内部のAPIなので、VoxCPMを更新するときは動作を確かめ直す。
  - S2: `voice add`のときにs2.cppが`<home>/cache/voices/s2/<名前>.s2voice`を作る。消えていれば、S2で使うときに録音から作り直す（約1分）。2026-11-11より前は`voices/`に置いていた（録音があるものは自動で移る）。
- `voices/`には取り直せない録音と文字起こしだけを置き、作り直せるプロファイルはすべて`cache/voices/`に置く。そのため`cache/`を丸ごと消しても声は失われない。キャッシュのプロファイルは消してよい（`voice build`か次の利用で作り直される）。

## 計測値（2026-11-11、MacBook Air M4・メモリ32 GB、本人の声、約100文字・16秒の原稿）

| エンジン | 生成時間 | 倍率 | 最初の音（`speak`） | ピークメモリ | 原稿どおり | 話者類似度 |
|---|---|---|---|---|---|---|
| OmniVoice（MPS・float16、まとめて1回） | 29.8秒 | 1.86倍 | 29.8秒（全文を1回で作るため） | 約4.1 GB | 一致 | 0.88 |
| OmniVoice（文ごとに4回） | 約60秒 | 約3.6倍 | 14.9秒 | | 一致 | 0.91 |
| VoxCPM2（MPS、torch 2.15、文ごと） | 約33秒（読み込みを除く） | 1.86〜2.12倍 | 4.7秒 | 約13.8 GB | 一致 | 0.94 |
| S2（Metal） | | 約7.8倍 | | 約4 GB | | |

- 原稿どおりかと話者類似度は、faster-whisper mediumの文字起こしとSpeechBrain ECAPA（別人は0.02）による機械の目安で、聞いて確かめたものではない。
- **OmniVoiceは1回ごとの固定の時間が大きい。** 10秒の参照音声では短い文でも約12秒かかった（参照なしなら2.6秒、ステップ数を16にすると6.1秒）。参照音声と読む文をまとめて毎回計算するためで、そのため`speak`・`say`・`api`は200文字まで（`[engines.omnivoice] request_chars`）まとめて送る。
- **VoxCPM2はtorchの版で速さが変わる。** 同じMacでtorch 2.8.0は1ステップ約0.47秒、2.15.0は約0.29秒だった。そのためMacだけtorch 2.15.0に固定している。
- VoxCPM2の`say`（生成しながら再生）: 最初の音は1.9秒で届くが、倍率が約2.2倍で実時間より遅い。途切れないよう、1文字あたり120ミリ秒（Macの既定。`[engines.voxcpm2] stream_start_buffer_ms_per_char`）を溜めてから流す。22文字の文で最初の音まで5.9秒、途切れは0秒だった。
- 1文ずつ生成すると、VoxCPM2で「本日は」が崩れたことがある（torch 2.8.0のとき、1回）。

## 版の固定

| エンジン | 版 | 理由 |
|---|---|---|
| OmniVoice | `omnivoice==0.2.1`、torch 2.8.0 | READMEの導入例と、比較のときに動かした版 |
| VoxCPM2 | VoxCPM `300e4260`（2026-11-09のGit）、Macはtorch 2.15.0、Windows・Linuxはtorch 2.8.0+cu128 | PyPIの2.0.3は2026-05で古い。torch 2.15のCUDA版は13.2用だけで、新しいNVIDIAドライバーが必要になる |

- 依存関係は`tools/engines/<エンジン>/uv.lock`に固定してある。`engine install`は`uv sync --frozen`で入れるので、ロックの外の版は入らない。
- WindowsとLinuxのtorchは、PyTorchのCUDA 12.8の配布元（`download.pytorch.org/whl/cu128`）から入る。Macは通常のPyPIの版（MPS対応）。
- 更新するときは`uv lock --project <local-tts>/tools/engines/<エンジン>`で作り直し、このMacで速さと読みを確かめ直してから、この表を書き換える。

## Windowsでの確認

**まだWindowsでは動かしていない。** 次の手順で確かめ、結果（各コマンドの出力と`<home>\cache\<エンジン>-server.log`の末尾）を共有してもらう。PowerShellで、`<local-tts>`はこのスキルのフォルダ。

1. 前提を確かめる。

   ```powershell
   nvidia-smi
   uv run --project "<local-tts>/tools" local-tts doctor
   ```

   `nvidia-smi`の右上の「CUDA Version」が12.8以上であること（ドライバーが対応する上限）。`doctor`の`engines`に3つのエンジンが並ぶこと。

2. 旧フォルダから移す（presenter-ttsを使っていたPCだけ）。

   ```powershell
   uv run --project "<local-tts>/tools" local-tts home migrate --dry-run
   uv run --project "<local-tts>/tools" local-tts home migrate
   ```

   Windowsではs2.cppのビルドもそのまま移る。移したあと`engine list`の`s2`が`ready`であること。

3. エンジンを入れる（約3 GBのPyTorchのCUDA版とモデルをダウンロードする）。

   ```powershell
   uv run --project "<local-tts>/tools" local-tts engine install omnivoice
   uv run --project "<local-tts>/tools" local-tts engine install voxcpm2
   ```

4. 声を作って時間を測る。

   ```powershell
   uv run --project "<local-tts>/tools" local-tts speak "<local-tts>/tools/examples/presentation.ssml" --engine omnivoice --output outputs/omni.wav --force
   uv run --project "<local-tts>/tools" local-tts speak "<local-tts>/tools/examples/presentation.ssml" --engine voxcpm2 --output outputs/vox.wav --force
   uv run --project "<local-tts>/tools" local-tts server status
   uv run --project "<local-tts>/tools" local-tts server stop
   ```

   見るところ: 結果のJSONの`rtf_speech`、サーバーのログの`device`が`cuda`であること、`server stop`のあと`server status`がすべて`not running`になること。

確かめたい点は次のとおり。

| 点 | 起こりうること |
|---|---|
| CUDA版torchの導入 | ドライバーが古いと`cuda`が使えず`cpu`になる（ログの`device`で分かる） |
| `torch.compile` | Windowsでは無効にしている。有効にするとTritonがなく失敗する |
| VRAM | RTX 3080（10 GB）では、VoxCPM2（約8 GB）とS2（約4 GB）を同時に動かせない。起動前に空きを確かめて止める |
| プロセスの確認 | 停止のとき、PIDの本人確認にPowerShellの`Get-CimInstance`を使う |
| 生成しながらの再生 | CUDAでは先に溜めない設定（0）にしている。途切れるなら`[engines.voxcpm2] stream_start_buffer_ms_per_char`を上げる |
