---
title: local-tts — ローカルで文章を音声にする
sidebar_label: local-tts
---

# local-tts

文章を外部のAPIへ送らず、手元のFish Audio S2 Pro（s2.cpp）で音声にしたいときに使います。その場での読み上げ、SSMLからのWAV生成、録音からの声の登録、OpenAI互換の音声APIの起動、不調の切り分け、キャッシュの片付けを扱います。

スライドへのナレーション付けや発表原稿の作成は扱いません。これらは、このリポジトリの外で配布されている`presenter`と`presentation-ja`の対象です。

## 導入と前提

hooksを同梱しない単一Skillなので、[`npx skills add`](../../plugins/distribution.md)で導入します。

```sh
npx skills add https://github.com/yukihito-jokyu/context/tree/main/utils/skills --skill local-tts --agent codex claude-code
```

| 項目 | 内容 |
| --- | --- |
| 対応環境 | Apple Silicon Mac＋Metal、またはWindows 10/11＋NVIDIA GPU（CUDA 12.4以上） |
| 必要なソフト | uv、FFmpeg。初回のビルドにはGit、CMake、WindowsはVisual Studio C++、MacはXcode Command Line Tools |
| 初回の準備 | エンジンのビルドに約20分、モデルの取得に数分。エージェントがライセンスへの同意とソフトの導入の承認を求めてから進めます |
| 必要なディスク | モデル・エンジンで約4 GB |
| 実行時のメモリ | TTSサーバーの起動中はGPUメモリ（Macではユニファイドメモリ）を約4 GB使います |

:::warning ライセンス
s2.cppとS2 Proのモデルは**Fish Audio Research License**で提供されます。研究・非商用の利用は無償ですが、商用利用にはFish Audioとの別途の契約が必要です。
:::

## 渡す情報

読み上げる文章またはSSMLファイル、出力先、使う声を渡します。声を登録する場合は、5〜30秒の録音、話している内容の正確な文字起こし、本人の声または本人の許可を得た声であることを伝えます。

## 依頼例

```text
local-ttsを使って、次の文章をWAVにしてください。出力先は outputs/greeting.wav です。音は再生しないでください。
本日はお集まりいただき、ありがとうございます。
```

## 進め方

1. `doctor`でエンジンの状態を確かめ、準備が必要なら承認を得てセットアップします。
2. 目的に合うコマンドを選びます。聞くだけなら`say`、ファイルに残すなら`speak`です。
3. `speak`では文章をSSMLに書き、`plan`で区切りを確かめてから合成します。
4. 出力の場所と長さ、使った声、聞いて確かめた範囲を報告します。
5. 使い終わったらTTSサーバーを止めます。

## 成果物の例

2文の日本語をSSMLにして区切りを確認し、ローカルのS2 Pro（Metal）でWAVを生成しました。公開サイトにはWAVを掲載せず、原稿・区切り・区間ごとの時間を掲載しています。

**到達点：WAVの生成とTTSサーバーの停止まで。音声の試聴は未実施。**

### 実行した依頼

```text
local-ttsを使って、次の2文をWAVにしてください。音は再生しないでください。既定の声を使います。
本日はお集まりいただき、ありがとうございます。発表の時間は十五分です。
```

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
# 音声ファイルの報告

| 項目 | 内容 |
|---|---|
| ファイル名 | `sample.wav`（実行用の作業場所に出力。公開物には含めていません） |
| 合計の長さ | 4.78秒（`ffprobe` の値は 4.783311 秒） |
| 形式 | PCM 16bit、44.1 kHz、モノラル |
| 使った声 | 設定の既定の声（`--voice` は付けていません） |
| 再生 | していません（`speak` を使用。`timing.json` の `playback_enabled` は `false`） |

## 聞いて確かめた範囲

ありません。この実行では音声を聞く手段がなかったため、読みと発音は誰も確かめていません。
長さと形式の確認は、聞いて確かめたことの代わりにはなりません。

## まだ聞いていない範囲
````

### 成果物を取得する

- [実行報告（Markdown）](pathname:///skills/local-tts/output.md#download)
- [合成に使ったSSML](pathname:///skills/local-tts/sample.ssml#download)
- [planの出力](pathname:///skills/local-tts/plan.txt#download)
- [区間ごとの時間（JSON）](pathname:///skills/local-tts/timing.json#download)
- [実行入力の原本](pathname:///skills/local-tts/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/local-tts/execution.json#download)

### 確認した結果

- doctorでengine.readyがtrueであることを確認
- planは発話2件で警告なし
- speakは終了コード0で、4.78秒の音声を約36秒で生成（実時間の約7.5倍）
- ffprobeで確かめたWAVの長さがtiming.jsonのaudio_secondsと一致
- server stop後にserver statusでnot runningを確認
- 実行者は音声を聞けないため、読みの正しさは未確認。WAVはFish Audio Research Licenseでの公開の扱いが未確認のため非掲載

## 確認するポイント

数字、英字、固有名詞を実際に聞いて確かめます。長さや音量の確認は、正しく読めたことの確認の代わりになりません。OpenAI互換APIは既定で`0.0.0.0:8000`に公開されるため、他の機器から使う必要がなければ`--host 127.0.0.1`で起動されているかを確認します。登録する声は本人または許可を得たものに限ります。

## 開発時のテスト

Skill専用のテストは`tools/tests/`にあり、リポジトリ全体のテストには含めません。`<local-tts>`を`utils/skills/media/local-tts`に置き換えて実行します。

```sh
uv run --project "<local-tts>/tools" python -m unittest discover -s "<local-tts>/tools/tests"
```

## 正本を読む

詳細な手順と制約は[local-ttsのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/media/local-tts/SKILL.md)を参照してください。
