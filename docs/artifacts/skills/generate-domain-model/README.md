# 定期契約と請求のドメインモデル

`generate-domain-model` を公開用TypeScriptコードへ実行したサンプルです。作成済みモデルやPNGの転用は行わず、`source/` の2つのコードファイルから4概念・3関係と3図を生成しました。

## 閲覧する

ZIPを展開して `catalog/index.html` をブラウザーで開きます。PNGとMermaidはHTMLにも埋め込まれているため、ネットワーク接続は不要です。図をクリックすると拡大し、カードの根拠を開くと実コードの抜粋を確認できます。

- `catalog/`: 検査済みHTML、モデル、コードのスナップショット、manifest、3組のMermaid・PNG
- `source/`: 公開用コードと元のREADME。`.git` とAgent設定は含みません。
- `report.md`: `run.py finish` が保存した本文
- `verification.json`・`verification/`: 実行した検査と限界、ブラウザー検査の実記録
- `screenshots/`: 幅1440pxと390pxでの実際の全ページ画像
- `input.md`: 実行した依頼

## 再生成する

Context Repositoryの `utils/skills/design/generate-domain-model/` にあるSkillと、インストール済みのPython 3.9以上、git、Mermaid CLI、Chromeを使います。`<skill>` をそのSkillの絶対パスへ置き換えてください。依存ツールの新規ダウンロードはこのサンプルの実行に含めていません。

```sh
git -C source init
python3 <skill>/scripts/install.py --project source
cd source
python3 <skill>/scripts/run.py start --set repo=. --set name=subscription-billing 'コードから根拠付きのドメインモデル図とカタログを作成してください。'
python3 <skill>/scripts/catalog.py inspect --state .skill-runs/generate-domain-model/state.json
cp ../catalog/model.json .skill-runs/generate-domain-model/out/subscription-billing/model.json
```

`MMDC` に既存のMermaid CLI、`PUPPETEER_EXECUTABLE_PATH` にブラウザーの実行ファイルを指定してから、次の順で実行します。

```sh
python3 <skill>/scripts/catalog.py build --state .skill-runs/generate-domain-model/state.json
python3 <skill>/scripts/run.py check
```

PNGとHTMLを開いて文字・関係・操作を確認し、未確認事項を `.skill-runs/generate-domain-model/notes.md` に箇条書きで残してから `python3 <skill>/scripts/run.py finish` を実行します。同梱モデルは入力コードに対応するため、コードを変えた場合は根拠も調査し直します。

このサンプルのコミット値は隔離検証用Gitのものです。再生成時のGit情報は異なり得ます。Entity分類、逆方向の件数制約、実行時の非null保証、オブジェクトの寿命の所有は未確認です。hooksは配置と登録を検査しましたが、信頼操作とセッション内での自動起動は実施していません。
