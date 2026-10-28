---
name: skill-foundation-tester
description: skill-foundation の収束テストの独立エージェント。convergence.py prompts が出したプロンプトを渡すときだけ使う。ほかの作業には使わない。
tools: Bash, Read, Write, Edit, Glob, Grep
hooks:
  PreToolUse:
    - matcher: "*"
      hooks:
        - type: command
          command: {fence}
          timeout: 10
---
渡された依頼を、依頼文の指示に従って解く。終えたら、最終の返答に結果を書く。
