# 変換環境を準備する

STEP-02：Python 3.9以上、Node.js、公式Mermaid CLIの `mmdc` と、Puppeteerで起動できるブラウザを使う。スキルはパッケージをインストールしない。CLIがないときは以下を利用者に示し、導入後に再実行する。

## 検証した構成

2026-10-27にMermaid CLI 12.0.0、Node.js [version redacted]、Python [version redacted]、既存のGoogle Chromeで確認した。Mermaid CLI 12.0.0はNode.js 22.13.0以上を要求する。生成・検査のPythonコードは3.9以上の構文と標準ライブラリで書く。別の版は `deps` と実際のPNG生成で確認する。

利用者が依存の追加を許可したときの、プロジェクト外の検証ディレクトリへの導入例である。

```sh
npm install --prefix /tmp/domain-model-tools --no-audit --no-fund @mermaid-js/mermaid-cli@12.0.0
```

npmがPuppeteerのインストールスクリプトを保留した場合は、npmの表示する手順でPuppeteerのブラウザ導入を許可するか、既にあるChromeを指定する。実行環境に合う方法を利用者が選ぶ。

```sh
export DOMAIN_MODEL_MMDC=/tmp/domain-model-tools/node_modules/.bin/mmdc
export PUPPETEER_EXECUTABLE_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
python3 <skill>/scripts/catalog.py deps
```

`PUPPETEER_EXECUTABLE_PATH` はブラウザが既に存在するときだけ指定する。OSが異なる場合はそのOSのブラウザの実行ファイルを指定する。描画のフォントはOSにある日本語フォントを使うため、版と環境が違うPNGのバイト一致は保証しない。

## 根拠

- [公式Mermaid CLI](https://github.com/mermaid-js/mermaid-cli)：Mermaid原本からPNGを生成するコマンド。
- [12.0.0のpackage.json](https://github.com/mermaid-js/mermaid-cli/blob/12.0.0/package.json)：Node.jsとPuppeteerの依存。
- [Puppeteer設定](https://pptr.dev/guides/configuration)：既存ブラウザの実行ファイルと環境変数。
- [MermaidのclassDiagram](https://mermaid.js.org/syntax/classDiagram.html)：概念、属性、関連、多重度の記法。
