# generate-domain-model plugin

[generate-domain-model](../../skills/design/generate-domain-model/SKILL.md)と、実行中の出力を検査するhooksを同梱する。正本はSkillディレクトリに置き、ビルドで正本全体をコピーする。Agent別のhooks設定は、同梱した共通ランタイムを直接呼び出す。

リポジトリのルートで実行する。

```sh
python3 utils/plugins/generate-domain-model/build.py --agent codex --output /tmp/domain-model-codex
python3 utils/plugins/generate-domain-model/build.py --agent claude-code --output /tmp/domain-model-claude
```

生成先は存在しないディレクトリを指定する。ビルドは配布物の生成だけを行う。利用方法と実際に確認した範囲は[利用ガイド](../../../docs/plugins/generate-domain-model.md)に記載する。
