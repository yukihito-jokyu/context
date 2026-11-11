# presenterからの切り出しと、名前の分離

このスキルは、[nogikun/presenter](https://github.com/nogikun/presenter)の`presenter`と`presenter-setup`（`main`、2026-11-08時点で導入した版）から、音声合成の単体運用の部分をコピーして作った。
元の`presenter`の`computedHash`（`skills-lock.json`）は`f2a5a1bd250465eddf175864000cea79e3507d67e01d9eae5f5ff06b348df91e`。

`npx skills`で元のスキルを更新しても、このスキルには反映されない。

## 2026-11-11に名前とデータのフォルダを分けた

当初はpresenterと声やエンジンを共有するため、名前を変えずに使っていた。VoxCPM2とOmniVoiceへの対応に合わせて、次のように分けた。

| 種類 | 旧 | 新 |
|---|---|---|
| Pythonパッケージ | `presenter_tts` | `local_tts` |
| uvプロジェクト・コマンド | `presenter-tts` | `local-tts` |
| 設定の見本 | `presenter.example.toml` | `local-tts.example.toml` |
| データのフォルダ | `~/.local/share/presenter-tts`、`%LOCALAPPDATA%\presenter-tts` | `~/.local/share/local-tts`、`%LOCALAPPDATA%\local-tts` |
| 環境変数 | `PRESENTER_TTS_HOME`、`PRESENTER_TTS_API_KEY` | `LOCAL_TTS_HOME`、`LOCAL_TTS_API_KEY`（旧名も警告付きで読む） |

- presenterとはデータを共有しない。旧フォルダの声・設定・APIキーは`local-tts home migrate`でコピーし、キャッシュは移動する。
- 旧名の環境変数は、移行のあいだだけ読む。新しい手順書や設定には旧名を書かない。

## 除いたもの

| 対象 | 理由 |
|---|---|
| `narrate.py`、`play.py`、`video.py`、`player.html` | スライドの音声化、プレーヤー、MP4の機能 |
| `cli.py`の`narrate`・`play`・`video`コマンド | 同上 |
| `tests/test_narrate.py`、`tests/test_play.py`、`test_cli.py`の該当テスト | 同上 |
| `references/playback-video.md` | 同上 |

## 変えたもの

- `tests/test_skill_layout.py`を、このスキルの構成を確かめる内容にした。
- 設定の見本の`parallel`の説明と、古い`docs/tts.md`への参照を直した。
- 手順書の`<presenter>`を`<local-tts>`にし、presenter-setupの手順を`references/setup.md`に移した。
- 上の表のとおり名前とデータのフォルダを分け、`home.py`（フォルダの決定と移し替え）を足した。

## presenterの修正を取り込むとき

名前を分けたので、ファイルを丸ごと上書きしない。

1. presenterを更新し、presenter側の`tools/src/presenter_tts/`と`<local-tts>/tools/src/local_tts/`を比べる（`diff -ru`）。差分のうち`presenter_tts`と`local_tts`の違いは名前の変更なので無視する。
2. 共通のファイル（`audio.py`、`ssml.py`、`voices.py`、`server.py`、`runtime.py`、`say.py`、`fillers.py`、`api.py`）の変更を確かめ、必要な部分だけを手で取り込む。
3. `cli.py`は、上の3コマンドを除いた状態と、このスキルで足したコマンドを保って手で合わせる。
4. テストを実行する。

   ```console
   uv run --project "<local-tts>/tools" python -m unittest discover -s "<local-tts>/tools/tests"
   ```

5. この文書のハッシュと日付を更新する。
