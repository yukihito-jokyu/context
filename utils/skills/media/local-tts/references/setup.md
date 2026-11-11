# セットアップ手順

使うエンジンとモデルを用意し、音が出るところまで確かめる。
`<local-tts>`はこのスキルのフォルダ。エンジンとモデルは`<home>/cache/`に置かれる。presenterスキルとは共有しないので、presenter側でビルド済みでも、このスキル用にもう一度用意する（旧フォルダからは`home migrate`で移せる）。
ユーザーにやってもらうのは、**ソフトの導入とライセンスへの同意の承認**だけにする。それ以外のコマンドはこちらで実行する。

## 0. どのエンジンを用意するか

既定はVoxCPM2。用途で選ぶ（[engines.md](engines.md)）。必要なものだけを用意すればよい。

| エンジン | 用意のしかた | 必要なもの | 容量 |
|---|---|---|---|
| OmniVoice | 下の「PyTorchのエンジン」 | uv、FFmpeg。WindowsはNVIDIA GPU（VRAM約4.5 GB以上、ドライバーがCUDA 12.8以上に対応） | 実行環境約1 GB、モデル約3 GB |
| VoxCPM2 | 下の「PyTorchのエンジン」 | 同上（VRAM約8 GB以上） | 実行環境約1.5 GB、モデル約5 GB |
| S2 | 手順1〜5（ビルド） | Git、CMake、WindowsはVisual StudioとCUDA Toolkit 12.4以上、MacはXcode CLT。**ライセンスへの同意** | 約4 GB |

### PyTorchのエンジン（OmniVoice・VoxCPM2）

1. `doctor`で`uv`・`ffmpeg`・`huggingface.co`を確かめる（足りなければ手順2の表で入れる）。Windowsは`nvidia-smi`の「CUDA Version」が12.8以上であること。
2. 入れるもの（PyTorchとモデル、上の表の容量）と時間（回線次第で数分〜十数分）を伝えて承認を得る。
3. 導入して確かめる。ダウンロードがあるので、時間がかかりそうならバックグラウンドで実行する。

   ```console
   uv run --project "<local-tts>/tools" local-tts engine install omnivoice
   uv run --project "<local-tts>/tools" local-tts engine list
   ```

4. 手順5と同じく音を確かめる（`say --engine omnivoice ...`）。設定の見本がなければ手順4の終わりのとおり置く。

ライセンスはどちらもApache-2.0で、S2のような同意は要らない。ただし、なりすまし・詐欺・偽情報への使用は禁じられている。
以下の手順1〜5はS2（s2.cpp）を用意するときのもの。

## 1. いまの状態を調べる

```console
uv run --project "<local-tts>/tools" local-tts doctor
```

uv自体がない場合はこのコマンドが動かないので、先に手順2でuvを入れる。
出力のJSONから次を読む。**`engine.ready`（S2の準備）がtrueなら手順5（動作確認）へ飛ぶ。**

| 項目 | 必要な状態 |
|---|---|
| `prerequisites.platform` | `windows`または`macos`。それ以外は未対応 |
| Macの`prerequisites.architecture` | Apple Siliconを示す`arm64` |
| Windowsの`gpu` | NVIDIAのGPUがあり、合計のVRAM（2つ目の値、MB）が6000以上 |
| Windowsの`prerequisites.cuda_version` | 12.4以上 |
| Windowsの`prerequisites.visual_studio_cpp` | パスがある（C++のビルドツールが入っている） |
| Macの`prerequisites.metal` | `xcrun --find metal`で見つかる |
| `prerequisites.git`、`prerequisites.uv` | パスがある |
| `ffmpeg`、`ffplay` | パスがある |
| Macの`swiftc` | パスがある（再生用の補助プログラムをビルドする。なければ再生はFFplayを使う） |
| `huggingface.co`、`github.com` | `DNS available` |

WindowsでGPUがない、またはVRAMが足りない場合は、セットアップを進めずにその旨を伝える（CPUだけでは実用的な速度にならない）。MacはApple SiliconとMetalが必要。

## 2. 足りないソフトを入れる

足りないものだけを一覧にし、**何を・どこから・どれくらいの容量で入れるか**を見せて、承認を得てから入れる。
大きなもの（Visual Studio、CUDA）は管理者権限が必要で、ダウンロードも数GBある。承認なしに入れない。

Windows:

| ソフト | 導入コマンド | 備考 |
|---|---|---|
| uv | `winget install --id astral-sh.uv -e` | |
| Git | `winget install --id Git.Git -e` | |
| FFmpeg（FFplayを含む） | `winget install --id Gyan.FFmpeg -e` | |
| Visual Studio 2022 C++ビルドツール | `winget install --id Microsoft.VisualStudio.2022.BuildTools -e --override "--wait --passive --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"` | CMakeも含まれる。数GB |
| CUDA Toolkit | `winget show --id Nvidia.CUDA --versions`で版を確かめ、12.4以上を`winget install --id Nvidia.CUDA -e --version <版>` | 約3 GB。GPUドライバーの更新は別に判断する |

- 導入後は、新しく開いたシェルでないとPATHが反映されないことがある。もう一度`doctor`を実行し、見つからない場合はフルパスで確かめる。
- CUDAが複数入っていて、PATHの先頭が古い版（11.xなど）のことがある。`C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\`の下で12.4以上の最も新しい版を選び、手順4で`-CudaRoot`に渡す。PATHは書き換えない。
- CUDAやWSLの細かい確認は[cuda-wsl.md](cuda-wsl.md)を読む。

Mac:

| ソフト | 導入コマンド | 備考 |
|---|---|---|
| Xcode Command Line Tools | `xcode-select --install` | GUIでの承認と完了待ちが必要。Git、clang++、Metalを含む |
| uv | `brew install uv` | Homebrewがない場合は、公式インストーラーを提示して承認を得る |
| FFmpeg（FFplayを含む） | `brew install ffmpeg` | Homebrewがない場合は、先に導入方法をユーザーと決める |

`xcode-select -p`、`xcrun --find clang++`、`xcrun --find metal`を確認する。CMakeがなければ`setup-s2.sh`がuvxで一時的に用意するため、CMakeだけをHomebrewへ追加しない。

## 3. ライセンスに同意をもらう

s2.cppのエンジンとS2 Proのモデルは**Fish Audio Research License**で提供される。ダウンロードの前に、次をユーザーに伝えて同意を得る。

- 研究・非商用の利用は無償。**商用利用にはFish Audioとの別途の契約が必要**（business@fish.audio）
- 配布するときはライセンス文と帰属表示（"This model is licensed under the Fish Audio Research License, Copyright © 39 AI, INC. All Rights Reserved."）が必要
- 全文は取得後の`<home>/cache/s2.cpp/LICENSE.md`

同意がなければ、ここで止める。

## 4. エンジンをビルドし、モデルを取得する

`doctor`の`prerequisites.platform`に従い、対応する片方だけで確認する（数秒）。

```powershell
& "<local-tts>/tools/scripts/setup-s2.ps1" -CheckOnly -CudaRoot "<CUDAのフォルダ>"
```

```bash
"<local-tts>/tools/scripts/setup-s2.sh" --check-only
```

確認結果がreadyなら、本番を**バックグラウンドで**実行する。s2.cppの取得とビルドに約20分、モデルのダウンロードに数分かかる。始める前に目安の時間を伝える。

```powershell
& "<local-tts>/tools/scripts/setup-s2.ps1" -CudaRoot "<CUDAのフォルダ>"
```

```bash
"<local-tts>/tools/scripts/setup-s2.sh"
```

- 置き場所は`%LOCALAPPDATA%\local-tts\cache\`（Windows）または`~/.local/share/local-tts/cache/`（Mac）。`LOCAL_TTS_HOME`があればその下。どのプロジェクトからも共有される。
- Windowsのビルド中に大量に出る`warning C4819`（文字コード）や`C4244`（型変換）は無害。どちらのOSも終わりに`Setup finished`が出れば成功。
- 失敗したら、出力の`error`を含む行を探す。WindowsはCUDA、MacはXcode/Metal/CMakeを確認する。同じビルド先を別のバックエンドで構成し直して拒否された場合は、`cache/s2-build`を消してからやり直す（ユーザーに確認してから）。
- モデルのダウンロードだけが失敗した場合、ビルドは残っている。もう一度同じコマンドを実行すればダウンロードから再開する。

設定ファイルがなければ、見本をコピーする（既存のものは上書きしない）。

```powershell
$ttsHome = if ($env:LOCAL_TTS_HOME) { $env:LOCAL_TTS_HOME } else { Join-Path $env:LOCALAPPDATA 'local-tts' }
$config = Join-Path $ttsHome 'config.toml'
if (-not (Test-Path -LiteralPath $config)) {
    New-Item -ItemType Directory -Path $ttsHome -Force | Out-Null
    Copy-Item "<local-tts>/tools/local-tts.example.toml" -Destination $config
}
```

Macでは同じ見本を`~/.local/share/local-tts/config.toml`へ置く。既存ファイルは上書きしない。

```bash
tts_home="${LOCAL_TTS_HOME:-$HOME/.local/share/local-tts}"
mkdir -p "$tts_home"
test -e "$tts_home/config.toml" || cp "<local-tts>/tools/local-tts.example.toml" "$tts_home/config.toml"
```

## 5. 音が出るか確かめる

```console
uv run --project "<local-tts>/tools" local-tts doctor
uv run --project "<local-tts>/tools" local-tts say --engine s2 "こんにちは。音声合成のテストです。"
```

`engine.ready`がtrueで、`say`がエラーなく終わったら、**ユーザーに聞こえたかを尋ねる**。
生成も再生も成功しているのに聞こえない場合は、OSの出力デバイスとミュートを確かめてもらう（よくある原因）。
サーバーの起動に失敗したら`<home>/cache/s2-server.log`（PyTorchのエンジンは`<home>/cache/<エンジン>-server.log`）の末尾を読む。GPUメモリまたはMacのユニファイドメモリ不足なら、`config.toml`の`[server] gpu_layers`を減らす（例: 18）。

確かめ終わったら、続けて使う予定がなければサーバーを止める（GPUのメモリを約4 GB使うため）。

```console
uv run --project "<local-tts>/tools" local-tts server stop
```

## 6. 声を登録する（任意）

既定の声はモデル自身の声で、文ごとに声質が変わることがある。発表に使うなら、声を1つ登録しておくとよい。
ユーザーが望んだ場合だけ、SKILL.mdの「声を登録する」の手順に従う（本人の声か許可を得た声だけ）。
登録したら、`config.toml`の先頭の`voice = "<名前>"`を有効にすると既定の声になる。

## 7. 報告する

次をまとめて伝える。

- 入れたソフトと版、用意したエンジン（S2はビルドしたバックエンド、CUDAまたはMetal）
- 置き場所（Windowsは`%LOCALAPPDATA%\local-tts`、Macは`~/.local/share/local-tts`）と使った容量
- 動作確認の結果（聞こえたかどうかを含む）
- 次にできること（`say`で話させる、`speak`でWAVを作る）と、片付けの方法（[cleanup.md](cleanup.md)）

## やり直すとき

- CUDA/Xcodeを更新した、ビルドが壊れた: `cache/s2-build`を消して手順4から。
- モデルを消した: 手順4をもう一度実行する（ビルドは使い回され、ダウンロードだけが走る）。
- PyTorchのエンジンの実行環境が壊れた: `<home>/cache/engines/<名前>/`を消して`engine install <名前>`をもう一度（モデルは残っていれば照合だけ）。
- 別のPCに移る: そのPCでこのスキルを最初から実行する。声は`<home>/voices/`をコピーすれば持っていける（エンジン別のプロファイルは向こうで作り直される）。
- 旧presenter-ttsのフォルダがある: [commands.md](commands.md)の8節の`home migrate`で移す。
