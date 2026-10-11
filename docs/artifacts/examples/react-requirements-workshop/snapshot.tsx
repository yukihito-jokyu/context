import { useState } from 'react'
import { DetailPage } from '@/components/patterns/detail-page'
import { Button } from '@/components/ui/button'
import { output } from './result-text'

export default function ArtifactGallery() {
  const [expanded, setExpanded] = useState(false)
  return <section data-screen-detail-target="artifact-view">
    <DetailPage title="unknownsの実行結果" description="未知の分類と、次に使うスキルを確認する">
      <section data-screen-detail-target="input"><h2>実行した依頼</h2><p>docsのすべてのスキル説明に実成果物を掲載する修正について、未知と必要な子スキルを整理してください。</p></section>
      <section data-screen-detail-target="output"><h2>実際の出力</h2><pre style={{whiteSpace:'pre-wrap',font:'inherit'}}>{expanded ? output : output.split('## 3.')[0]}</pre></section>
      <Button data-review-target="expand" data-screen-detail-target="expand" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>{expanded ? '抜粋へ戻る' : '全文を表示'}</Button>
      <a data-review-target="download" data-screen-detail-target="download" download="unknowns.md" href={'data:text/markdown;charset=utf-8,' + encodeURIComponent(output)}>Markdown原本をダウンロード</a>
    </DetailPage>
  </section>
}
