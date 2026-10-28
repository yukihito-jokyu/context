1. 依頼から「3. 入力」の項目を読み取る。表で「start の前に聞く」とある項目が依頼に無ければ、ここでまとめてユーザーに聞く（CTL-03）
2. `python3 <skill>/scripts/run.py start --set ticket=<チケットID> "<依頼文>"` を実行する。終了コード3なら、出力された質問をユーザーに聞き、答えを `--set` で渡してやり直す（CTL-01）
3. `python3 <skill>/scripts/collect_diff.py` を実行する。終了コード4なら IN-01、終了コード2なら STEP-04 に従って中断する。出力に出たファイルと差分だけを材料にする。git はこのスクリプトの中だけで使い、`git add`・`git commit` を実行しない（IN-02、STEP-01、STEP-03）
4. 1行目を `<チケットID> <要約>` の形で書く。チケットIDは start が出した `ticket` の値を使い、要約は「<対象>を<動詞>する」の形にする。`[skip ci]` のような CI を止める記法は書かない（OUT-02、OUT-03、OUT-04、OUT-05、OUT-06）
5. 2行目を空行にし、3行目から本文を、collect_diff.py が出した「本文の単位」と STEP-02 の場合分けに従って書く。形は見本 `assets/examples/commit-message.txt` と同じにする。書いたものを `.skill-runs/write-commit-message/out/commit-message.txt` に保存する（OUT-01、STEP-02）
6. `python3 <skill>/scripts/run.py check` を実行する。「整形」で始まる行は check が契約の format で自動で直した記録なので、ファイルを読み直す。指摘があれば、ルールIDを「4. ルール」で引いて出力を直す。検査や契約を変えて通さない（CTL-02）
7. 決めきれなかったことがあれば `.skill-runs/write-commit-message/notes.md` に「- 」の箇条書きで書き、`python3 <skill>/scripts/run.py finish` を実行する。終了コード1なら手順6に戻る。終了コード0なら、出力された本文をそのまま返答する（RPT-01）
