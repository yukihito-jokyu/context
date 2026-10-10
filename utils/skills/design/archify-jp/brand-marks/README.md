# 組み込みブランドマーク

Archifyには、architecture、workflow、sequence、dataflow、lifecycleの各ノードで
よく使われる107ブランドの範囲を限定したカタログが同梱されています。マークは
著者が任意で指定する識別情報であり、ノードのセマンティックな`type`、色、ラベル、
関係を置き換えるものではありません。

未知のサイトは、明示的な2段階のワークフローで処理します。最初に
`node bin/archify.mjs brands capture <url> --json`を実行し、返されたダイジェスト固定の
`brand`値を記述します。通常のrenderおよびvalidateコマンドは、固定されていない
取得を実行しません。内容が変更されている場合や利用できない場合は、安全側に倒して
処理を失敗させます。

大部分のベクターパスとブランドメタデータは、Simple Icons 16.28.0から生成されています。
OpenAIのマークは、OpenAI公式ブランドガイドラインを出典としています。生成された各項目は、
出典と、上流で提供されている場合はガイドラインおよびライセンスのメタデータを
`renderers/shared/generated-brand-marks.mjs`に記録します。

ブランド名とロゴは、それぞれの所有者の商標である場合があります。Simple Iconsの
CC0ライセンスが対象とするのはコレクション作成作業であり、基になったすべての商標や
アートワークではありません。コントリビューターは、マークを追加または更新する前に、
記録された出典、最新のブランドガイドライン、想定する参照目的での利用を確認する必要が
あります。Archifyは、スポンサー関係、推奨、提携を示唆するものではありません。

`catalog.json`を編集した後、コミット対象のランタイム依存関係がないバンドルを再生成します。

```bash
npm run generate:brand-marks
npm run check:brand-marks
```

`renderers/shared/generated-brand-marks.mjs`を手作業で編集しないでください。
