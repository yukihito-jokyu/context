# ローカルのエンジンのセットアップ

リモートのAPIが使えないときに生成を引き継ぐ、このPCのエンジンを準備する手順。
ローカルの生成は**local-ttsスキル**（このスキルの隣の`.claude/skills/local-tts`、`<local-tts>`と書く）が行う。remote-ttsはエンジンのコードを持たない。

ユーザーにやってもらうのは、**ソフトの導入とライセンスへの同意の承認**だけにする。それ以外のコマンドはこちらで実行する。

## 1. いまの状態を調べる

```console
python3 "<remote-tts>/scripts/rtts.py" check
uv run --project "<local-tts>/tools" local-tts engine list
```

- `check`の`local_ready`がtrueなら準備はできている。`local_engine`が切り替えたときに使うエンジン。
- `local-tts`が「旧フォルダに声が残っている」と止まったら、local-ttsの`home migrate`で移す（[local-ttsのコマンド](../../local-tts/references/commands.md)）。声を扱うので、`--dry-run`の結果を見せて承認を得てから実行する。
- local-ttsスキル自体がなければ、ローカルへの切り替えは使えない。`--no-fallback`で使うか、local-ttsを導入する。

## 2. エンジンを用意する

既定のエンジンはlocal-ttsの設定（`engine`、既定はVoxCPM2）で決まる。`--engine`で選んだエンジンだけ用意すればよい。

| エンジン | 用意のしかた | ライセンス |
|---|---|---|
| OmniVoice | `uv run --project "<local-tts>/tools" local-tts engine install omnivoice`（約1 GBの実行環境と約3 GBのモデル） | Apache-2.0 |
| VoxCPM2 | `uv run --project "<local-tts>/tools" local-tts engine install voxcpm2`（約1.5 GBの実行環境と約5 GBのモデル） | Apache-2.0 |
| S2 Pro | local-ttsの[セットアップ手順](../../local-tts/references/setup.md)（ビルドに約20分） | Fish Audio Research License（商用は別契約。同意が必要） |

- どれもソフトの導入とダウンロードを伴うので、容量と時間を伝えて承認を得てから実行する。
- 終わったら`engine list`で`ready`になったことを確かめる。

## 3. 声を合わせる

切り替えても同じ声で作れるよう、リモートと同じ名前の声をローカルにも登録しておく（本人の声か許可を得た声だけ）。

```console
uv run --project "<local-tts>/tools" local-tts voice list
uv run --project "<local-tts>/tools" local-tts voice add <名前> "<録音>" --text "<録音で話している内容>"
```

同じ録音でも、エンジンが違えば声の印象は変わる。切り替わった音声は、声の違いに注意するようユーザーに伝える。

## 4. 報告する

- 用意したエンジンと、使った容量（`<home>/cache/engines/`、`<home>/cache/huggingface/`）
- `check`の結果（`local_ready`と`local_engine`）
- 次にできること（リモートが止まっていても音声を作れること）
