# APIの詳細と実測値

2026-11-10に、LAN内のMacから別PCのAPIへ接続して測定した。サーバーが更新されると変わりうる。
「実装より」と書いた項目は、同系統のコード（local-ttsスキルの`tools/src/local_tts/api.py`）を読んだ結果で、実機では再現させていない。

## エンドポイント

| メソッドとパス | 内容 |
|---|---|
| `GET /v1/models` | `s2-pro`、`tts-1`、`tts-1-hd`、`gpt-4o-mini-tts`を返す |
| `POST /v1/audio/speech` | 音声を生成する |

どちらも`Authorization: Bearer <APIキー>`が必要。ほかのパス（`/health`、`/docs`、声の一覧など）は404。

## リクエスト項目

| 項目 | 内容 | 実測 |
|---|---|---|
| `input` | 文章。4096文字まで。本文全体は64 KBまで | 空・超過は400 |
| `voice` | 登録済みの声の名前 | 下の「声の解決」 |
| `response_format` | `mp3`（既定）、`opus`、`aac`、`flac`、`wav`、`pcm` | すべて生成を確認 |
| `speed` | 0.25〜4.0 | 範囲外は400。1.0で1.81秒の文が、0.25で7.75秒、0.5で3.75秒、2.0で1.04秒、4.0で0.52秒 |
| `model` | 無視される | 存在しない名前でも200 |

`speed`は生成後の変換なので、生成時間は変わらない（どの速度でも約8秒）。

## 形式

| 形式 | Content-Type | 中身 |
|---|---|---|
| `mp3` | `audio/mpeg` | 44.1 kHz、モノラル、128 kbps |
| `opus` | `audio/ogg` | 48 kHz、Ogg、64 kbps |
| `aac` | `audio/aac` | 44.1 kHz、ADTS、128 kbps |
| `flac` | `audio/flac` | 44.1 kHz。ヘッダーに長さが入らない |
| `wav` | `audio/wav` | 44.1 kHz、16ビット、モノラル。サイズ欄は`0xFFFFFFFF`、音声データは78バイト目から |
| `pcm` | `audio/pcm` | ヘッダーなし、24 kHz、16ビット、モノラル |

## 声の解決

同じ28文字を生成し、基本周波数の中央値とスペクトルの差を比べた。

| `voice` | 基本周波数の中央値 | 判定 |
|---|---|---|
| `myvoice`（2回） | 322 Hz、317 Hz | 登録された声 |
| 省略 | 123 Hz | サーバーの既定の声 |
| `alloy` | 124 Hz | 同上（エラーにならない） |
| `no-such-voice` | 122 Hz | 同上（エラーにならない） |
| `default` | 209 Hz | クローンなしのモデルの声。1回のみの測定 |

判定は音響的な比較によるもので、聞いて確かめたものではない。

## 速度

| 入力 | 音声 | 所要時間 | 倍率 |
|---|---|---|---|
| 12文字 | 約2秒 | 約8秒 | 約4.1倍 |
| 28文字 | 約4.4秒 | 約18秒 | 約4.4倍 |
| 273文字 | 48.4秒 | 233秒 | 約4.8倍 |

- 最初のデータが届くのは先頭の文の生成後（273文字で24秒）。文の途中では届かない。
- 1文字あたり約0.18秒の音声になる。
- 4096文字に近い入力は試していない。

## サーバーの挙動

- 合成は1件ずつ。3件を同時に送ると8.1秒、16.8秒、26.5秒に完了し、エラーは出なかった。
- クライアントが切断すると処理は止まり、次のリクエストはほぼ通常の時間（8.7秒）で完了した。
- 文は`。！？!?`で分かれ、40文字を超える文はさらに`、`で分かれる（実装より）。
- 英語の`.`では分かれない（実装より）。
- 生成に温度0.8のサンプリングを使うため、同じ入力でも結果は毎回変わる（再生成で4.37秒と4.55秒）。

## エラー

| 状況 | HTTP | メッセージ |
|---|---|---|
| キーなし・誤り | 401 | `Missing or wrong API key` |
| JSONでない | 400 | `The request body must be JSON` |
| `input`が空・なし | 400 | `'input' must be a non-empty string` |
| 4096文字超 | 400 | `'input' is longer than 4096 characters` |
| 本文が64 KB超 | 400 | `The request body is missing or too large` |
| 形式が不正 | 400 | `'response_format' must be one of ...` |
| 速度が範囲外 | 400 | `'speed' must be a number from 0.25 to 4.0` |
| 句読点のみ | 503 | `No speech generated` |
| 不明なパス | 404 | `Unknown path: ...` |
| `OPTIONS` | 501 | CORSのプリフライトが通らないので、ブラウザから直接は呼べない |

本文はOpenAI形式（`{"error": {"message", "type", "param", "code"}}`）。501だけはHTML。

## 未確認のこと

- `[laugh]`、`[whisper]`などのインラインタグが効くか。タグ付きの文は1秒ほど長く、冒頭に0.4秒の無音があったが、演技になったのか読み上げられたのかは聞かないと分からない。
- 数字、英字の読みの正確さ。
- 長時間の連続生成での安定性。

## OpenAI SDKから呼ぶ

実機で動作を確認した形（`openai`パッケージ）。キーはコードに書かず、設定から読む。

```python
import json, os
from openai import OpenAI

config = json.load(open(os.path.expanduser("~/.config/remote-tts/config.json")))
client = OpenAI(base_url=config["base_url"], api_key=config["api_key"], timeout=3600)
with client.audio.speech.with_streaming_response.create(
    model="tts-1", voice="myvoice", input="こんにちは。", response_format="mp3"
) as response:
    response.stream_to_file("out.mp3")
```

- `timeout`は長くする。順番待ちの間は何も届かない。
- `voice`は必ず登録済みの名前を明示する。
- OpenAIの型定義にない声の名前で型チェッカーが警告を出すことがあるが、実行には問題ない。
- 長い文章は文の切れ目で数百字ずつに分けて送ると、失敗時のやり直しが小さく済む。

## curlで呼ぶ

```bash
curl -fsS --max-time 1800 "$RTTS_BASE_URL/audio/speech" \
  -H "Authorization: Bearer $RTTS_API_KEY" -H 'Content-Type: application/json' \
  -d '{"model":"tts-1","voice":"myvoice","input":"こんにちは。","response_format":"mp3"}' \
  -o out.mp3
```

`RTTS_BASE_URL`は設定の`base_url`と同じ値（例: `http://<サーバーのIP>:8000/v1`）。
`curl`の終了コードを確かめる。18なら途中で切れている。
