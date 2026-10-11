# 依存スキルを読む・同期する

このパッケージはArchifyを`vendor/archify-jp`に同梱する。制作者は最初にその`SKILL.md`を読み、対象の型のスキーマ・例・必要な参照だけを追加で読む。グローバルのArchifyや他版のCLIを混ぜない。vendorのファイルは直接変更しない。

## 同期

Python 3.9以上、Node.js 18以上、npm/npx、導入元の日本語版を読める環境で、次を実行する。カレントディレクトリは任意で、スクリプト自身がパッケージ位置を解決する。

```sh
python3 /path/to/compare/scripts/sync_vendor.py
python3 /path/to/compare/scripts/sync_vendor.py --check
```

同期スクリプトは`dependencies.json`を読み、固定したskills CLI版で`npx skills@1.7.2 add ~/.agents/skills/archify-jp --skill archify-jp --agent codex --copy --yes`を実行する。スクリプトはvendor内の一時プロジェクトへ取得し、必須ファイルとコピー内容を確認した後に`vendor/archify-jp`へ移す。グローバルのスキルは変更しない。取得失敗・タイムアウト・不完全な導入では既存版を残す。同時同期は`.sync.lock`で防止する。プロセスを強制終了した場合は残ったロックや`.archify.previous`を確認して復旧する。

`dependencies.lock.json`には実際の取得元、スキル名、パッケージ版、内容ハッシュ、実行引数、skills CLIのロックを記録する。`--check`はネットワークを使わず、その内容と必須ファイルを検査する。`--dry-run`は実行予定の引数を表示する。同期後にはvendorの指示を読み直し、スキーマ・配布・画像エクスポートの互換性を確認する。既定の同期元は`~/.agents/skills/archify-jp`であり、ホームディレクトリは実行するユーザーの環境で解決する。英語版の公式リポジトリへ切り替えない。

同梱版はContext Repositoryの正本`utils/skills/design/archify-jp`を明示的な同期元として、固定版skills CLIで取得した`archify-jp` 2.16.0です。ライフサイクルv2、意味の凡例、種類ごとの既定配色を含みます。取得元と内容ハッシュは`dependencies.lock.json`に記録しています。今回は既定のホーム配置を使っていないため、`configured_source_sync_verified`はfalseです。これは同期の失敗ではなく、明示した同期元が設定上の既定値と異なることを表します。vendorには元のMITライセンスを保持します。

ローカルの日本語版から明示的に同期する場合は次を使う。スクリプトはネットワーク失敗を理由に勝手にローカル版へ切り替えない。

```sh
python3 scripts/sync_vendor.py --source /path/to/context/utils/skills/design/archify-jp --skill archify-jp
```

固定版skills CLIが既にあるnpmプロジェクトをオフラインで利用する場合は`--cli-prefix /path/to/npm-project`を指定する。このパスは`node_modules/skills/package.json`を持つ必要がある。CLI版がmanifestと違えばスクリプトは停止する。

## 図を生成する

Archifyのコマンドは同梱版の`SKILL.md`に従う。2.16版では次のように検証・配布する。出力は読者の成果物フォルダへ保存し、vendorへ生成物を書き込まない。

```sh
node /path/to/compare/vendor/archify-jp/bin/archify.mjs validate workflow model.json --quality showcase --json
node /path/to/compare/vendor/archify-jp/bin/archify.mjs deliver workflow model.json diagram.html --quality showcase --json
```

制作者は型付きモデルに`meta.visual_preset: "editorial"`を設定し、モデルと配布レシートを保存する。新しい版の配布手順を古いコマンドへ無理に合わせない。特に更新版の`finalize`がブラウザ検査を要求する場合、そのゲートを省略して成功と報告しない。

## 画像エクスポート

第一選択は配布HTMLの標準エクスポート。読者がエクスポートするPNG/SVGと同じ表示を求める場合、制作者は実際の標準エクスポートを取得して埋め込み、確認した条件を記録する。画像生成器や独自のSVG描き直しで代用しない。

ブラウザが利用できない場合、2.16.0用の補助スクリプトは同梱テンプレートの**変更していないserializeSvg関数**を限定DOMアダプターで実行できる。制作者はこれをブラウザでの操作やPNG一致の検証として報告しない。補助スクリプトは異なる版では停止する。更新後は標準ブラウザエクスポートを使い、必要なら互換性を検証してから補助スクリプトを更新する。

```sh
python3 scripts/export_standard_svg.py diagram.html diagram.svg --model model.json
```

この補助処理はPython標準ライブラリとNode.jsだけを使い、完全なviewBoxとノードの保持を検査する。背景・グリッド・凡例・フォント・記号・配色を省略しない。`.export.json`は生成経路と未確認のブラウザ一致を記録する。検査用の別ラスタライザーによるPNGを標準PNGとして埋め込まない。
