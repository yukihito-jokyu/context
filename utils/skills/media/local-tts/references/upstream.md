# presenterからの切り出し

このスキルは、[nogikun/presenter](https://github.com/nogikun/presenter)の`presenter`と`presenter-setup`（`main`、2026-11-08時点で導入した版）から、音声合成の単体運用の部分をコピーして作った。
元の`presenter`の`computedHash`（`skills-lock.json`）は`f2a5a1bd250465eddf175864000cea79e3507d67e01d9eae5f5ff06b348df91e`。

`npx skills`で元のスキルを更新しても、このスキルには反映されない。

## 除いたもの

| 対象 | 理由 |
|---|---|
| `narrate.py`、`play.py`、`video.py`、`player.html` | スライドの音声化、プレーヤー、MP4の機能 |
| `cli.py`の`narrate`・`play`・`video`コマンド | 同上 |
| `tests/test_narrate.py`、`tests/test_play.py`、`test_cli.py`の該当テスト | 同上 |
| `references/playback-video.md` | 同上 |

## 変えたもの

- `tests/test_skill_layout.py`を、このスキルの構成を確かめる内容にした。
- `presenter.example.toml`の`parallel`の説明と、古い`docs/tts.md`への参照を直した。
- 手順書の`<presenter>`を`<local-tts>`にし、presenter-setupの手順を`references/setup.md`に移した。

コマンド名`presenter-tts`、パッケージ名`presenter_tts`、データの保存先`<home>`は、presenterと声やエンジンを共有するために変えていない。

## 修正を取り込むとき

1. presenterを更新し、`.agents/skills/presenter/tools/src/presenter_tts/`と`<local-tts>/tools/src/presenter_tts/`を比べる（`diff -ru`）。
2. 共通のファイル（`audio.py`、`ssml.py`、`voices.py`、`server.py`、`runtime.py`、`say.py`、`fillers.py`、`api.py`）の変更を確かめて取り込む。
3. `cli.py`は、上の3コマンドを除いた状態を保って手で合わせる。
4. テストを実行する。

   ```console
   uv run --project "<local-tts>/tools" python -m unittest discover -s "<local-tts>/tools/tests"
   ```

5. この文書のハッシュと日付を更新する。
