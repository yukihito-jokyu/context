---
title: remote-tts — LAN上の別PCで文章を音声にする
sidebar_label: remote-tts
---

# remote-tts

LAN上の別PCで動いているOpenAI互換の音声合成API（local-ttsの`/v1/audio/speech`）を使い、文章やテキストファイルをWAV・MP3などの音声にします。GPUのある別PCで生成し、APIが止まっている・つながらないときは、このPCのlocal-ttsへ自動で切り替えます。接続の確認、401や接続エラー、声が違うといった不調の切り分け、OpenAI SDKからこのAPIを呼ぶコードを書くときにも使います。

「remote-ttsで」「別のPCで音声にして」のように、別PCやリモートのAPIでの生成を明示したときに使います。指定のない「読み上げて」だけの依頼は[local-tts](local-tts.md)の対象です。

## 導入と前提

hooksを同梱しない単一Skillなので、[`npx skills add`](../../plugins/distribution.md)で導入します。ローカルへの切り替えには隣にlocal-ttsが必要なので、一緒に導入します。

```sh
npx skills add https://github.com/yukihito-jokyu/context/tree/main/utils/skills --skill remote-tts --skill local-tts --agent codex claude-code
```

| 項目 | 内容 |
| --- | --- |
| このPC | Python 3.8以上。WAV以外の出力にはFFmpeg |
| APIを動かすPC | local-ttsを導入し、`local-tts api`でAPIを起動しておきます。起動と停止はそのPCのセッションで行います |
| 接続の設定 | `~/.config/remote-tts/config.json`に`base_url`（例: `http://<サーバーのIP>:8000/v1`）、`api_key`、`voice`、`known_voices`を書きます。環境変数`RTTS_BASE_URL`・`RTTS_API_KEY`でも指定できます |
| ローカルへの切り替え | 隣のlocal-tts、uv、用意済みのエンジン（OmniVoice・VoxCPM2・S2のどれか）。未セットアップなら切り替えずにエラーになります |
| 所要時間の目安 | リモートで1文字あたり約0.85秒。千字で約14分です |

:::warning APIキーと声
APIキーを知っている人は、登録した声で何でも話させられます。キーは設定ファイルか環境変数に置き、コードや報告に書き写しません。クローンする声は本人の声か、本人の許可を得た声に限ります。
:::

## 渡す情報

読み上げる文章またはテキストファイル、出力先（拡張子で形式が決まります）、使う声を渡します。声を揃えたい本番の音声など、リモートでの生成を確実にしたいときは「ローカルに切り替えない」と伝えます。段落の間を空けたいときは、空ける秒数も伝えます。

## 依頼例

```text
remote-ttsを使って、次の文章をWAVにしてください。出力先は outputs/greeting.wav です。音は再生しないでください。
本日はお集まりいただき、ありがとうございます。
```

## 進め方

1. `check`でリモートのAPIとキーが使えるか確かめます。使えなければ、ローカルで生成できるかも合わせて調べます。
2. `--dry-run`で文の分割と所要時間の目安を出します。1分を超えるなら、目安を伝えてからバックグラウンドで実行します。
3. 英字や数字を読ませたい形に直し、`speak`で音声にします。途中で止まったら、同じコマンドで続きから再開します。
4. 結果の`backend`を見て、リモートとローカルのどちらで生成したかを伝えます。ローカルに切り替わったら、その理由と声の違いに注意することを伝えます。
5. ファイルの場所と長さ、使った声、聞いて確かめた範囲とまだ聞いていない範囲を報告します。

## 成果物の例

2文をremote-ttsで音声にしようとしましたが、リモートのAPIが接続タイムアウトになったため、このPCのlocal-tts（VoxCPM2）へ切り替えて8.0秒のWAVを生成しました。公開サイトにはWAVを掲載せず、check・dry-run・speakの結果と報告を掲載しています。サーバーのIP、絶対パス、個人名は伏せ字にしています。

**到達点：ローカルへ切り替えてのWAVの生成まで。リモートでの生成と音声の試聴は未実施。**

### 実行した依頼

```text
remote-ttsを使って、次の2文をWAVにしてください。音は再生しないでください。設定の既定の声を使います。
本日はお集まりいただき、ありがとうございます。発表の時間は十五分です。
```

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
# 音声ファイルの報告

| 項目 | 内容 |
|---|---|
| ファイル名 | `greeting.wav` |
| 合計の長さ | 8.0秒 |
| 形式 | WAV（PCM 16bit、48 kHz、モノラル） |
| 使った声 | `myvoice`（設定の既定の声） |
| 生成した環境 | **local**（このPCのlocal-tts、エンジンはVoxCPM2） |
| 再生の有無 | 再生していない |

## リモートからローカルへの切り替え

リモートのAPIにつながらなかったため、このPCのlocal-ttsへ切り替えて全文を生成しました。

- 理由（`fallback_reason`）: `Cannot reach http://<サーバーのIP>:8000/v1: timed out`
````

### 成果物を取得する

- [実行報告（Markdown）](pathname:///skills/remote-tts/output.md#download)
- [checkの結果（JSON）](pathname:///skills/remote-tts/check.json#download)
- [分割と所要時間の目安（JSON）](pathname:///skills/remote-tts/dry-run.json#download)
- [speakの結果（JSON）](pathname:///skills/remote-tts/result.json#download)
- [実行入力の原本](pathname:///skills/remote-tts/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/remote-tts/execution.json#download)

### 確認した結果

- checkでリモートのAPIがタイムアウトし、backendがlocal（local_readyがtrue、エンジンはvoxcpm2）であることを確認
- dry-runで35文字・1リクエスト、リモートの目安30秒、ローカルの目安1分10秒と出ることを確認
- speakはリモートにつながらずローカルのVoxCPM2へ切り替わり、終了コード0で53.4秒かけてWAVを生成
- 結果のJSONで、声が設定の既定のmyvoiceで、fallback_reasonが接続タイムアウトであることを確認
- ffprobeで8.0秒・16bit PCM・48 kHz・モノラルのWAVで、audio_secondsと一致することを確認
- 切り替えで起動したローカルのサーバーが終了後に自動で止まっていることを確認
- 末尾まで無音がないため語尾が切れている可能性があり、試聴が必要な箇所として記録。実行者は音声を聞けないため読みの正しさは未確認

## 確認するポイント

結果の`backend`が`remote`か`local`かを確かめます。ローカルに切り替わった音声は、同じ声の名前でもリモートとは声が違うことがあります。APIは未登録の声の名前をエラーにせず別の声で返すので、新しく登録した声は設定の`known_voices`に追加します。数字、英字、固有名詞を実際に聞いて確かめます。長さや音量の確認は、正しく読めたことの確認の代わりになりません。使い終わったら、APIを動かすPCでサーバーを止めます。

## 正本を読む

詳細な手順と制約は[remote-ttsのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/media/remote-tts/SKILL.md)を参照してください。APIの実測値とエラーの一覧は[api-notes.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/media/remote-tts/references/api-notes.md)にあります。
