---
title: loop-bgm — 設計図からループBGMを作る
sidebar_label: loop-bgm
---

# loop-bgm

動画やゲーム、配信に使うオリジナルのループBGMがほしいときに使います。テンポ・調・パートごとの演奏をTOMLの設計図に書き、プログラムで音にします。同じ設計図からは常に同じ音ができ、気になる行だけを直せます。楽器音はすべて数式合成なので、音源素材のダウンロードや権利表記は要りません。

既存の録音（mp3など）のカットや編集、外部の音楽生成サービス向けのプロンプト作成、音楽理論だけの質問は扱いません。効果音の切り出しと、鼻歌からのメロディ抽出は未実装です。

## 導入と前提

hooksを同梱しない単一Skillなので、[`npx skills add`](../../plugins/distribution.md)で導入します。

```sh
npx skills add https://github.com/yukihito-jokyu/context/tree/main/utils/skills --skill loop-bgm --agent codex claude-code
```

| 項目 | 内容 |
| --- | --- |
| 必要なソフト | uv。Pythonとnumpyはuvが自動で用意します |
| 試聴（任意） | ループ再生にはsoxの`play`、1周の再生には`afplay`（macOS）を使います |
| 作業場所 | カレントフォルダの`songs/`に設計図、`output/`に音源を置きます |

## 渡す情報

用途と雰囲気を渡します。テンポ、調、小節数、声やナレーションを重ねるかが決まっていれば一緒に伝えます。曖昧な依頼でも、エージェントは用途から妥当な値を決めて作り始めます。

## 依頼例

```text
loop-bgmを使って、ブラウザゲームのタイトル画面に流す、明るいループBGMを作ってください。8小節で、ナレーションは重ねません。
```

```text
さっきの曲のテンポを少し速くして、ベースを控えめにしてください。ゲームボーイ風でも書き出してください。
```

## 進め方

1. `uv`があることを確かめます。
2. テンポと調、リズム、ベース、コード、メロディ、アレンジ、ミックスの順に`songs/<曲名>.toml`を書きます。
3. 通常版、または`--style gameboy`でゲームボーイ風のWAVを`output/`に書き出します。
4. 出力された「つなぎ目」と「パート別」の数値を見て、必要なら`gain_db`を直して書き出し直します。
5. 数値で確かめた範囲と、聴いて判断してほしい点を分けて報告します。

修正の依頼では、テンポなら`bpm`、楽器なら該当パートの`instrument`というように、該当する行だけを編集します。

## 成果物の例

ブラウザゲームのタイトル画面向けに、BPM 152・D majorの8小節のループBGMを設計図から作り、通常版とゲームボーイ風のWAVを書き出しました。数式合成の音なので、WAVもそのまま掲載しています。

**到達点：通常版とゲームボーイ風のWAVの書き出しと、音量の確認まで。音の試聴は未実施。**

### 実行した依頼

```text
loop-bgmを使って、ブラウザゲームのタイトル画面に流す、明るいループBGMを作ってください。8小節で、ナレーションは重ねません。通常版とゲームボーイ風の両方を書き出してください。音は再生しないでください。
```

### 実出力の抜粋

以下は保存した原本の冒頭です。全文は原本から取得できます。

````markdown
# タイトル画面用ループBGM 実行結果

ブラウザゲームのタイトル画面に流す、明るい8小節ループBGMを作りました。通常版とゲームボーイ風の両方を書き出してあります。音は再生していません。

## 成果物

| 種類 | パス |
| --- | --- |
| 設計図 | `songs/title_screen.toml` |
| 通常版 | `output/title_screen/title_screen.wav`（パート別の音源は `output/title_screen/stems/`） |
| ゲームボーイ風 | `output/title_screen_gameboy/title_screen_gameboy.wav`（チャンネル別の音源は `output/title_screen_gameboy/stems/`） |
| 実行ログ | `render.log` |

## 曲の設計

| 項目 | 内容 |
````

### 成果物を取得する

- [通常版のWAV](pathname:///skills/loop-bgm/title_screen.wav#download)
- [ゲームボーイ風のWAV](pathname:///skills/loop-bgm/title_screen_gameboy.wav#download)
- [設計図（TOML）](pathname:///skills/loop-bgm/title_screen.toml#download)
- [書き出しのログ](pathname:///skills/loop-bgm/render.log#download)
- [実行報告（Markdown）](pathname:///skills/loop-bgm/output.md#download)
- [実行入力の原本](pathname:///skills/loop-bgm/input.md#download)
- [実行・検証記録（JSON）](pathname:///skills/loop-bgm/execution.json#download)

### 確認した結果

- 通常版・ゲームボーイ風ともに、render.logの「つなぎ目」がOK
- どちらも長さ12.632秒、-16.0 LUFS、リミッターの作用0.00%
- afinfoで48 kHz、16bit、2チャンネルのWAVであることを確認
- 最終の設計図で再度書き出し、両方のWAVのハッシュが一致することを確認
- 通常版は打楽器とコードのgain_dbを上げて、音量の目安に近づくよう調整
- ゲームボーイ風のch2とch3は見本の目安より1.7〜1.9 dB小さいが、gain_dbが効かないため未調整
- 実行者は音を聴けないため、雰囲気・メロディ・つなぎ目の聞こえ方は未確認

## 確認するポイント

エージェントは音を聴けません。数値で確かめられるのはつなぎ目と音量の目安までなので、雰囲気、メロディ、音色、ループの自然さは実際に聴いて判断します。

納品はWAVのままにします。MP3は前後に無音が付き、ループに隙間ができるためです。つなぎ目が要確認になったときは、波形を後から切らず、曲末と曲頭のパターンを見直します。

## 正本を読む

詳細な手順と設計図の書式は[loop-bgmのSKILL.md](https://github.com/yukihito-jokyu/context/blob/main/utils/skills/media/loop-bgm/SKILL.md)を参照してください。
