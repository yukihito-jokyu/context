# ローカルデータの片付け

local-ttsが手元に置くデータを、何を消してよいかと一緒に整理し、確かめてから消す手順。
`<home>`はWindowsでは`%LOCALAPPDATA%\local-tts`、Macでは`~/.local/share/local-tts`（環境変数`LOCAL_TTS_HOME`があればその値）。`<local-tts>`はこのスキルのフォルダ。

`<home>`はpresenterスキル（旧フォルダ`presenter-tts`）とは別にある。旧フォルダを消すかどうかは、presenterや古い版のremote-ttsを今後も使うかを確かめてから決める。旧フォルダには、移し替えのあとも声・設定のコピーが残っている（`home migrate`はコピーで、旧フォルダの声を消さない）。

## 置いてあるもの

| 場所 | 中身 | 目安 | 消したら | 消してよいか |
|---|---|---|---|---|
| `<home>/cache/models/` | S2 Proのモデルとトークナイザー | 約3.4 GB | 次の[セットアップ](setup.md)で再ダウンロード（数分） | よい |
| `<home>/cache/s2-build/` | ビルドしたs2.cpp | 約0.3 GB | 再ビルド（約20分） | よい |
| `<home>/cache/s2.cpp/` | s2.cppのソース | 約0.1 GB | 再取得（ビルドと同時） | よい |
| `<home>/cache/engines/` | OmniVoice・VoxCPM2の実行環境（PyTorchなど） | 各約1〜1.5 GB（WindowsのCUDA版は数GB） | 次の`engine install`で入れ直す（数分） | よい |
| `<home>/cache/huggingface/` | OmniVoice・VoxCPM2のモデル | 約3 GB、約5 GB | 次の`engine install`で再ダウンロード | よい |
| `<home>/cache/voices/` | エンジン別の声のプロファイル（`s2/`の`.s2voice`、`omnivoice/`・`voxcpm2/`の`.pt`） | 数MB | 次に使うときに録音から作り直す（S2は1つ約1分） | よい |
| `<home>/cache/fillers/` | エンジンと声ごとのフィラーのキャッシュ | 数MB | 次の`say`で自動で作り直す | よい |
| `<home>/cache/*.log`、`validation/`、`tmp/` | ログと診断結果 | 小さい | なし | よい |
| `<home>/voices/` | 登録した声の録音（`.wav`）と文字起こし（`.json`）、元の録音（`sources/`）。録音のない古い声は`.s2voice`だけがここにある | 数MB | **取り直せない**。録音と文字起こしから登録し直すしかない | **ユーザーが声ごとに明示したときだけ** |
| `<home>/config.toml` | 設定 | 小さい | 既定値に戻る | 確認してから |
| `<home>/api-key.txt` | OpenAI互換APIのキー | 小さい | 次の`api`で別のキーになる（接続中のアプリの設定が使えなくなる） | 確認してから |
| `<local-tts>/tools/.venv/` | Pythonと依存パッケージ | 約50 MB | 次の`uv run`で自動で作り直す | よい |
| `<作業フォルダ>/outputs/` | `say`・`speak`・`voice add`の出力 | 小さい | なし | 確認してから |

## 手順

### 1. 何がどれだけあるかを調べる

```powershell
$h = if ($env:LOCAL_TTS_HOME) { $env:LOCAL_TTS_HOME } else { Join-Path $env:LOCALAPPDATA 'local-tts' }
Get-ChildItem -Force $h, (Join-Path $h 'cache') -ErrorAction SilentlyContinue | ForEach-Object {
  $bytes = if ($_.PSIsContainer) { (Get-ChildItem -Recurse -Force -File $_.FullName -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum } else { $_.Length }
  '{0,-32} {1,10:N1} MB' -f $_.FullName.Substring($h.Length + 1), ($bytes / 1MB)
}
uv run --project "<local-tts>/tools" local-tts voice list
```

PowerShellの`$home`は予約済みの変数なので、別の名前（ここでは`$h`）を使う。

Macでは次のように確認する。

```bash
tts_root="${LOCAL_TTS_HOME:-$HOME/.local/share/local-tts}"
du -sh "$tts_root" "$tts_root"/* 2>/dev/null
uv run --project "<local-tts>/tools" local-tts voice list
```

### 2. 消す範囲を決めて、ユーザーに見せる

ユーザーの目的から範囲を選び、**消すパス、容量、消したあとに起きること**を一覧にして確認を取る。確認なしに消さない。

| 目的 | 消す範囲 |
|---|---|
| 少し空けたい | `cache/fillers/`、ログ、`validation/`、`tmp/` |
| 大きく空けたいが、また使う | 使わないエンジンの`cache/huggingface/hub/models--...`と`cache/engines/<名前>/`、S2なら`cache/models/`（再ダウンロードは数分。ビルドは残す） |
| エンジンを作り直したい | `cache/s2-build/`と`cache/s2.cpp/`（その後[セットアップ](setup.md)で再ビルド） |
| 当面使わない | `cache/`をまるごと（声と設定は残る） |
| 完全に消したい | 下の「アンインストール」 |

声を消すのは、ユーザーが**どの声を消すかを名前で言ったとき**だけ。「全部消して」と言われても、声が含まれることを伝えて、もう一度確かめる。

### 3. TTSサーバーを止める

ビルドやモデルを使っているサーバーが動いていると、ファイルを消せない。

```console
uv run --project "<local-tts>/tools" local-tts server stop
uv run --project "<local-tts>/tools" local-tts server status
```

`listening`のままで「started elsewhere」と出たら、このツール以外が起動したサーバー（手動で起動したs2.cppやエンジン）が動いている。ユーザーに止めてもらう。

### 4. 消す

確認した範囲だけを、パスを明示して消す。ワイルドカードで`<home>`の外まで広げない。

```powershell
Remove-Item -Recurse -Force (Join-Path $h 'cache\models')
```

Macでは`tts_root`の絶対パスが`/`やホームディレクトリそのものではないことを確認し、同じく対象を`<home>/cache/models/`のように完全に特定してから削除する。`$HOME`や`<home>`全体へ再帰削除をかけない。可能なら先にゴミ箱へ移す。

声は専用のコマンドで消す（声のファイル、参考音声、文字起こし、その声のフィラーをまとめて消す）。

```console
uv run --project "<local-tts>/tools" local-tts voice remove <名前> --yes
```

### 5. 消えたことと、残したものを確かめる

手順1をもう一度実行し、空いた容量と、残した声・設定を伝える。
エンジンやモデルを消した場合は、次に使う前に[セットアップ](setup.md)が必要になることも伝える。

## アンインストール

1. サーバーを止める（手順3）。
2. 消すものをユーザーに見せる。**声・設定・APIキーも消えること**を明示して、確認を取る。声を残したい場合は、先に`<home>/voices/`を別の場所へコピーしてもらう。
3. `<home>`をまるごと消す。声・設定・APIキーも消えるので、残したいものがないかを確かめてから行う。

   ```powershell
   Remove-Item -Recurse -Force $h
   ```

   Macでは解決した`<home>`の絶対パスを再確認してから、フォルダごとゴミ箱へ移す。`$HOME`や`~`を削除対象にしない。

4. `<local-tts>/tools/.venv`を消す（スキル自体を残す場合も、次の`uv run`で作り直される）。
5. スキル自体を消す場合は、`.claude/skills/local-tts/`を消す（`npx skills`の管理外なので、削除コマンドでは消えない）。

CUDA Toolkit、Visual Studio、Xcode Command Line Tools、Homebrew、FFmpeg、uvなど、セットアップで入れた（または入っていた）システムのソフトは、ほかのソフトも使っている可能性がある。消すかどうかはユーザーが決める。このスキルからは消さない。
