---
title: local-tts — ローカルで文章を音声にする
sidebar_label: local-tts
---

# local-tts

文章を外部のAPIへ送らず、手元の音声合成エンジン（Qwen3-TTS・VoxCPM2・OmniVoice・Fish Audio S2 Pro）で音声にしたいときに使います。その場での読み上げ、SSMLからのWAV生成、録音からの声の登録、エンジンの導入と切り替え、OpenAI互換の音声APIの起動、不調の切り分け、旧presenter-ttsフォルダからの移し替え、キャッシュの片付けを扱います。

スライドへのナレーション付けや発表原稿の作成は扱いません。これらは、このリポジトリの外で配布されている`presenter`と`presentation-ja`の対象です。LAN上の別PCで動くAPIを使う場合は[remote-tts](remote-tts.md)を使います。

## 導入と前提

hooksを同梱しない単一Skillなので、[`npx skills add`](../../plugins/distribution.md)で導入します。

```sh
npx skills add https://github.com/yukihito-jokyu/context/tree/main/utils/skills --skill local-tts --agent codex claude-code
```

| 項目 | 内容 |
| --- | --- |
| 対応環境 | Apple Silicon Mac（Qwen3-TTS・VoxCPM2・OmniVoiceはMPS、S2はMetal）、またはWindows 10/11＋NVIDIA GPU（Qwen3-TTS・VoxCPM2・OmniVoiceはCUDA 12.8版PyTorch、S2はCUDA 12.4以上）。Windowsでの動作はまだ確認していません |
| 必要なソフト | uv、FFmpeg。S2のビルドにはGit、CMake、WindowsはVisual Studio C++、MacはXcode Command Line Tools |
| 初回の準備 | 使うエンジンだけを導入します。Qwen3-TTSは実行環境約1.3 GBとモデル約4.2 GB、VoxCPM2は実行環境約1.5 GBとモデル約5 GB、OmniVoiceは約1 GBと約3 GB、S2はビルドに約20分。エージェントが容量と時間を伝え、承認を得てから進めます |
| 実行時のメモリ | エンジンのサーバーの起動中、Qwen3-TTSは約6.6 GB、VoxCPM2は約14 GB（CUDAは約8 GB）、OmniVoiceとS2は約4 GB使います（Macではユニファイドメモリ） |
| 生成の速さ | Apple M4で、Qwen3-TTSは音声の長さの約1.7倍、VoxCPM2とOmniVoiceは約2倍、S2は約8倍の時間がかかります。初回はモデルの読み込みに20〜30秒かかります |

| エンジン | 向いている用途 | ライセンス |
| --- | --- | --- |
| Qwen3-TTS（既定） | Apple M4ではいちばん速い。録音から登録した声で話します | Apache-2.0 |
| VoxCPM2 | 最初の音が早い。生成しながら再生できます | Apache-2.0 |
| OmniVoice | メモリが少ない環境。長い文をまとめて生成すると速くなります | Apache-2.0 |
| S2 Pro | 以前に作った音声と声をそろえたいとき | Fish Audio Research License |

:::warning ライセンス
S2（s2.cppとS2 Proのモデル）は**Fish Audio Research License**で提供されます。研究・非商用の利用は無償ですが、商用利用にはFish Audioとの別途の契約が必要です。Qwen3-TTS・VoxCPM2・OmniVoiceはApache-2.0ですが、なりすまし・詐欺・偽情報への使用は禁じられています。
:::

## 渡す情報

読み上げる文章またはSSMLファイル、出力先、使う声を渡します。エンジンを指定したい場合は、その名前も伝えます。声を登録する場合は、5〜30秒の録音、話している内容の正確な文字起こし、本人の声または本人の許可を得た声であることを伝えます。

## 依頼例

```text
local-ttsを使って、次の文章をWAVにしてください。出力先は outputs/greeting.wav です。音は再生しないでください。
本日はお集まりいただき、ありがとうございます。
```

## 進め方

1. `doctor`と`engine list`で使うエンジンの状態を確かめ、準備が必要なら承認を得て導入します。
2. 目的に合うコマンドを選びます。聞くだけなら`say`、ファイルに残すなら`speak`です。
3. `speak`では文章をSSMLに書き、`plan`で区切りを確かめてから合成します。エンジンは`--engine`で選びます。保存するWAVの大きさは、YouTubeの推奨（-14 LUFS）にそろえます。
4. `check`で文ごとの読みをカタカナで聞き取り、エージェントが原稿の文脈と照らして誤読を見つけます。長音や助詞の書き方の違いは直さず、カナ1文字でも音が抜けたり変わったりしたものは誤読として扱います。誤読した文だけを`redo`で作り直し、もう一度`check`します（3回まで）。初回は聞き取り用の環境とモデル（合わせて約4 GB）を、承認を得てから入れます。
5. 出力の場所と長さ、使った声とエンジン、`check`の結果、聞いて確かめた範囲を報告します。
6. 使い終わったらエンジンのサーバーを止めます。

## 成果物の例

2文の日本語をSSMLにして区切りを確認し、Qwen3-TTSと既定の声で5.28秒のWAVを生成しました。checkで2区間の読みをカタカナで聞き取り、原稿と照らして誤読がないと判断したため、redoは行っていません。保存したWAVの大きさは-14.1 LUFSでした。公開サイトにはWAVを掲載せず、原稿・区切り・区間ごとの時間・聞き取った読みを掲載しています。声の名前は伏せ字にしています。

**到達点：WAVの生成、checkによる読みの確認、server stopの実行まで。音声の試聴は未実施。**

### 実行した依頼

```text
local-ttsを使って、次の2文をWAVにしてください。音は再生しないでください。声は既定のもの、エンジンはQwen3-TTSを使います。読み間違いがないか確かめて、あれば直してください。
本日はお集まりいただき、ありがとうございます。発表の時間は十五分です。
```

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
2文をWAVにしました。音は再生していません。

- ファイル：`sample.wav`（区間ごとの時間は`sample.json`）
- 長さ：5.28秒（24 kHz、モノラル）
- 声：`<既定の声>`（設定の既定の声）
- エンジン：Qwen3-TTS
- 生成時間：約11.2秒（音声の約2.1倍）
- 音量：-14.1 LUFS、トゥルーピーク -1.9 dBFS

## 読みの確認（check）

`check`で区間ごとに読みを聞き取り、原稿と照らし合わせました。

| 区間 | 原稿 | 聞き取った読み | 判断 |
|---|---|---|---|
| 1 | 本日はお集まりいただき、ありがとうございます。 | ホンジツワオアツマリイタダキアリガトーゴザイマス | 正しい（「本日」はホンジツ） |
````

### 成果物を取得する

- [実行報告（Markdown）](pathname:///skills/local-tts/output.md#download)
- [合成に使ったSSML](pathname:///skills/local-tts/sample.ssml#download)
- [planの出力](pathname:///skills/local-tts/plan.txt#download)
- [区間ごとの時間（JSON）](pathname:///skills/local-tts/timing.json#download)
- [checkの出力（JSON）](pathname:///skills/local-tts/check.json#download)
- [実行入力の原本](pathname:///skills/local-tts/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/local-tts/execution.json#download)

### 確認した結果

- doctorとengine listで、既定のエンジンqwen3-ttsがready、checkの実行環境とモデルが導入済みであることを確認
- server statusで、Qwen3-TTSとOmniVoiceのサーバーが実行前から別に起動されている（started elsewhere）ことを確認
- planは発話2つ、警告0件
- speakは再生せずに5.28秒の音声を生成（生成11.2秒、発話の約2.1倍）
- FFmpegのebur128で、保存したWAVの大きさが-14.1 LUFS、トゥルーピークが-1.9 dBFSであることを確認
- checkは終了コード0で2区間を約9.6秒で聞き取り。区間1はホンジツワオアツマリイタダキアリガトーゴザイマス、区間2はハッピョーノジカンワジューゴフンデス
- 実行者が原稿と照らし、2区間とも読みは正しい（本日＝ホンジツ、十五分＝ジューゴフン）と判断。助詞のワと長音は表記の違いとして扱い、redoは不要
- server stopは「No server started by this tool is running」。実行前から別に起動されていたサーバーは止めていない
- 実行者は音声を聞けないため、アクセントとイントネーションは未確認。WAVは公開物に含めていない

## 確認するポイント

数字、英字、固有名詞を実際に聞いて確かめます。長さや音量の確認は、正しく読めたことの確認の代わりになりません。1本の音声の中でエンジンを混ぜないよう、作り直すときは前と同じエンジンを指定します。OpenAI互換APIは既定で`0.0.0.0:8000`に公開されるため、他の機器から使う必要がなければ`--host 127.0.0.1`で起動されているかを確認します。登録する声は本人または許可を得たものに限ります。使い終わったら`server stop`でエンジンのサーバーを止め、メモリを空けます。

## 開発時のテスト

Skill専用のテストは`tools/tests/`にあり、リポジトリ全体のテストには含めません。`<local-tts>`を`utils/skills/media/local-tts`に置き換えて実行します。

```sh
uv run --project "<local-tts>/tools" python -m unittest discover -s "<local-tts>/tools/tests"
```

## 正本を読む

詳細な手順と制約は[local-ttsのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/media/local-tts/SKILL.md)を参照してください。
