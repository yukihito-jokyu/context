import { useCallback, useEffect, useRef, useState, type MouseEvent, type PointerEvent, type ReactNode } from 'react'

type Point = { number: number; title: string; description: string; status?: string; approval_history?: { approved_in_snapshot: string; title: string }[]; target_key: string }
type Detail = { number: number; key: string; target_key: string; region: string; name: string; type: string; description: string; capability: string; behavior: string; trigger: string; result: string; failure: string }
type Position = { x_percent: number; y_percent: number; width_percent: number; height_percent: number }
type FixedAnnotation = { number: number; target_key?: string; padding_px?: number } & Partial<Position>
type Metadata = { snapshot: { number: number; slug: string; label: string; note?: string }; project: { title: string; subtitle?: string }; review_points: Point[]; screen_details: Detail[]; fixed_annotations?: FixedAnnotation[] }
type Target = { selector: string; target_key: string | null; tag: string; text: string }
type FeedbackItem = { number: number; kind: 'review_point' | 'dom_annotation'; status_at_render: string; previously_approved: boolean; reopened: boolean; title: string; approved: boolean; comment: string; target: Target | null; position: Position | null }
type CustomNote = { number: number; target: Target; position: Position; approved: boolean; comment: string }
type Box = { key: string; number: number; top: number; left: number; width: number; height: number; kind: 'point' | 'detail' | 'custom' }

const textTags = new Set(['SPAN', 'STRONG', 'SMALL', 'EM', 'B', 'I', 'P', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6'])
const behaviorLabels: Record<string, string> = { screen_transition: '画面遷移', backend_request: 'バックエンド通信', local_state_change: '画面内の変更', external_navigation: '外部ページへ移動', display_only: '表示のみ' }
const settle = (callback: () => void) => requestAnimationFrame(() => requestAnimationFrame(callback))

function selectableTarget(origin: HTMLElement, root: HTMLElement): HTMLElement | null {
  if (!root.contains(origin) || origin === root) return null
  const interactive = origin.closest<HTMLElement>('button,a,input,select,textarea,label,[role="button"]')
  if (interactive && root.contains(interactive)) return interactive
  if (!textTags.has(origin.tagName)) return origin
  const region = origin.closest<HTMLElement>('[data-review-target],article,li,tr,td,th,fieldset,details,summary')
  return region && root.contains(region) ? region : origin.parentElement !== root ? origin.parentElement : origin
}

function selectorFor(element: HTMLElement, root: HTMLElement): string {
  if (element.dataset.reviewTarget) return `[data-review-target="${element.dataset.reviewTarget}"]`
  const parts: string[] = []
  for (let node: HTMLElement | null = element; node && node !== root; node = node.parentElement) {
    const parent: HTMLElement | null = node.parentElement
    if (!parent) break
    const peers = Array.from(parent.children).filter(child => child.tagName === node!.tagName)
    parts.unshift(`${node.tagName.toLowerCase()}:nth-of-type(${peers.indexOf(node) + 1})`)
  }
  return parts.join(' > ')
}

function targetText(element: HTMLElement): string {
  return (element.getAttribute('aria-label') || element.getAttribute('placeholder') || element.getAttribute('title') || element.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 120)
}

function positionFor(element: HTMLElement, root: HTMLElement): Position {
  const rect = element.getBoundingClientRect()
  const area = root.getBoundingClientRect()
  const width = root.scrollWidth || area.width
  const height = root.scrollHeight || area.height
  const clamp = (value: number) => Number(Math.max(0, Math.min(100, value)).toFixed(2))
  return { x_percent: clamp((rect.left - area.left + root.scrollLeft) / width * 100), y_percent: clamp((rect.top - area.top + root.scrollTop) / height * 100), width_percent: clamp(rect.width / width * 100), height_percent: clamp(rect.height / height * 100) }
}

function downloadFeedback(snapshotId: string, payload: unknown) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2) + '\n'], { type: 'application/json' }))
  const link = document.createElement('a')
  link.href = url
  link.download = `${snapshotId}-feedback.json`
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function Review({ metadata, children }: { metadata: Metadata; children: ReactNode }) {
  const [mode, setMode] = useState<'points' | 'details'>('points')
  const [showPointBoxes, setShowPointBoxes] = useState(true)
  const [showDetailBoxes, setShowDetailBoxes] = useState(true)
  const [boxes, setBoxes] = useState<Box[]>([])
  const [hover, setHover] = useState<Box | null>(null)
  const [items, setItems] = useState<FeedbackItem[]>(() => metadata.review_points.map(point => ({ number: point.number, kind: 'review_point', status_at_render: point.status ?? 'pending', previously_approved: Boolean(point.approval_history?.length), reopened: point.status === 'reopened', title: point.title, approved: point.status === 'approved', comment: '', target: null, position: null })))
  const [custom, setCustom] = useState<CustomNote[]>([])
  const [detailComments, setDetailComments] = useState<Record<string, string>>({})
  const [detailsApproved, setDetailsApproved] = useState(false)
  const [openDetail, setOpenDetail] = useState(metadata.screen_details[0]?.key ?? '')
  const [generalComment, setGeneralComment] = useState('')
  const [message, setMessage] = useState('')
  const [selecting, setSelecting] = useState(false)
  const canvas = useRef<HTMLDivElement>(null)
  const customTargets = useRef(new Map<number, HTMLElement>())
  const snapshotId = `${String(metadata.snapshot.number).padStart(3, '0')}-${metadata.snapshot.slug}`
  const showBoxes = mode === 'points' ? showPointBoxes : showDetailBoxes

  const measure = useCallback(() => {
    const root = canvas.current
    if (!root) return
    const area = root.getBoundingClientRect()
    const fromElement = (key: string, number: number, element: HTMLElement, kind: Box['kind'], padding = 0): Box => {
      const rect = element.getBoundingClientRect()
      return { key, number, kind, top: rect.top - area.top + root.scrollTop - padding, left: rect.left - area.left + root.scrollLeft - padding, width: rect.width + padding * 2, height: rect.height + padding * 2 }
    }
    if (mode === 'details') {
      setBoxes(metadata.screen_details.flatMap(detail => {
        const target = [...root.querySelectorAll<HTMLElement>('[data-screen-detail-target]')].find(node => node.dataset.screenDetailTarget === detail.target_key)
        return target ? [fromElement(detail.key, detail.number, target, 'detail', 3)] : []
      }))
      return
    }
    const fixed: FixedAnnotation[] = metadata.fixed_annotations ?? metadata.review_points.map(point => ({ number: point.number, target_key: point.target_key, padding_px: 0 }))
    const pointBoxes = fixed.flatMap(annotation => {
      const point = metadata.review_points.find(item => item.number === annotation.number)
      if (!point) return []
      if (annotation.target_key) {
        const target = [...root.querySelectorAll<HTMLElement>('[data-review-target]')].find(node => node.dataset.reviewTarget === annotation.target_key)
        return target ? [fromElement(`point-${point.number}`, point.number, target, 'point', annotation.padding_px ?? 8)] : []
      }
      if (annotation.x_percent === undefined || annotation.y_percent === undefined || annotation.width_percent === undefined || annotation.height_percent === undefined) return []
      return [{ key: `point-${point.number}`, number: point.number, kind: 'point' as const, top: root.scrollHeight * annotation.y_percent / 100, left: root.scrollWidth * annotation.x_percent / 100, width: root.scrollWidth * annotation.width_percent / 100, height: root.scrollHeight * annotation.height_percent / 100 }]
    })
    const customBoxes = custom.flatMap(note => {
      let target = customTargets.current.get(note.number)
      if (!target?.isConnected && note.target.selector) {
        try { target = root.querySelector<HTMLElement>(note.target.selector) ?? undefined } catch { target = undefined }
      }
      return target ? [fromElement(`custom-${note.number}`, note.number, target, 'custom')] : []
    })
    setBoxes([...pointBoxes, ...customBoxes])
  }, [custom, metadata, mode])

  useEffect(() => {
    const root = canvas.current
    if (!root) return
    const observer = new ResizeObserver(() => settle(measure))
    const mutations = new MutationObserver(records => {
      if (records.some(record => !(record.target as Element).closest('.review-overlay'))) settle(measure)
    })
    observer.observe(root)
    root.querySelectorAll<HTMLElement>('[data-review-target],[data-screen-detail-target]').forEach(node => observer.observe(node))
    mutations.observe(root, { childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'style', 'hidden'] })
    const onScroll = () => settle(measure)
    root.addEventListener('scroll', onScroll, true)
    window.addEventListener('resize', onScroll)
    settle(measure)
    return () => { observer.disconnect(); mutations.disconnect(); root.removeEventListener('scroll', onScroll, true); window.removeEventListener('resize', onScroll) }
  }, [measure])

  const onPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (!selecting || mode !== 'points' || !canvas.current) return
    const target = selectableTarget(event.target as HTMLElement, canvas.current)
    if (!target) return setHover(null)
    const rect = target.getBoundingClientRect()
    const area = canvas.current.getBoundingClientRect()
    setHover({ key: 'hover', number: 0, kind: 'custom', top: rect.top - area.top + canvas.current.scrollTop, left: rect.left - area.left + canvas.current.scrollLeft, width: rect.width, height: rect.height })
  }

  const onCanvasClick = (event: MouseEvent<HTMLDivElement>) => {
    if (!selecting || mode !== 'points' || !canvas.current) return
    const target = selectableTarget(event.target as HTMLElement, canvas.current)
    if (!target) return
    event.preventDefault()
    event.stopPropagation()
    const used = new Set([...metadata.review_points.map(point => point.number), ...custom.map(note => note.number)])
    let number = 1
    while (used.has(number)) number++
    customTargets.current.set(number, target)
    setCustom(previous => [...previous, { number, target: { selector: selectorFor(target, canvas.current!), target_key: target.dataset.reviewTarget ?? null, tag: target.tagName.toLowerCase(), text: targetText(target) }, position: positionFor(target, canvas.current!), approved: false, comment: '' }].sort((a, b) => a.number - b.number))
    setSelecting(false)
    setHover(null)
    settle(() => { document.getElementById(`custom-feedback-${number}`)?.focus(); measure() })
  }

  const focusFeedback = (box: Box) => {
    if (box.kind === 'detail') {
      setOpenDetail(box.key)
      settle(() => document.getElementById(`detail-feedback-${box.key}`)?.focus())
      return
    }
    const id = box.kind === 'custom' ? `custom-feedback-${box.number}` : `point-feedback-${box.number}`
    document.getElementById(id)?.focus()
    settle(measure)
  }

  const selectDetail = (detail: Detail) => {
    setOpenDetail(previous => previous === detail.key ? '' : detail.key)
    const target = [...(canvas.current?.querySelectorAll<HTMLElement>('[data-screen-detail-target]') ?? [])].find(node => node.dataset.screenDetailTarget === detail.target_key)
    target?.scrollIntoView({ block: 'center', inline: 'nearest' })
    target?.classList.add('review-target-active')
    setTimeout(() => target?.classList.remove('review-target-active'), 1600)
    settle(measure)
  }

  const payload = () => ({
    schema_version: 1,
    snapshot_id: snapshotId,
    submitted_at: new Date().toISOString(),
    items: [...items, ...custom.map(note => ({ number: note.number, kind: 'dom_annotation' as const, status_at_render: 'pending', previously_approved: false, reopened: false, title: '選択要素への指摘', approved: note.approved, comment: note.comment.trim(), target: note.target, position: note.position }))].sort((a, b) => a.number - b.number),
    screen_detail_feedback: metadata.screen_details.map(detail => ({ detail_key: detail.key, comment: detailComments[detail.key]?.trim() ?? '' })).filter(item => item.comment),
    screen_details_approved: metadata.screen_details.length === 0 || detailsApproved,
    general_comment: generalComment.trim(),
  })

  const send = async () => {
    const data = payload()
    try {
      const response = await fetch('/api/feedback', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
      if (!response.ok) throw new Error((await response.json()).error ?? String(response.status))
      setMessage('保存しました。AI が待機していない場合は送信完了をチャットでも伝えてください。')
    } catch {
      downloadFeedback(snapshotId, data)
      setMessage('受信サーバーに接続できなかったため JSON をダウンロードしました。作業領域の discussion/ に置き、AI に伝えてください。')
    }
  }

  return <div className="review-shell" data-review-mode={mode}>
    <main className="review-stage">
      <header><div><strong>{metadata.project.title}</strong><p>{metadata.project.subtitle}</p></div><span>{metadata.snapshot.label}</span></header>
      <div className="review-frame-label"><span>画面案</span><small>{metadata.snapshot.note ? `${metadata.snapshot.note} · ` : ''}枠内を操作して確認</small></div>
      <div className={`review-canvas ${selecting ? 'selecting' : ''}`} ref={canvas} onPointerMoveCapture={onPointerMove} onPointerLeave={() => setHover(null)} onClickCapture={onCanvasClick}>
        {children}
        <div className="review-overlay">
          {showBoxes && boxes.map(box => <div key={box.key} className={`review-box ${box.kind}`} style={{ top: box.top, left: box.left, width: box.width, height: box.height }}><button type="button" className="review-number" aria-label={`注釈${box.number}のコメントへ移動`} tabIndex={selecting ? -1 : 0} onClick={() => focusFeedback(box)} style={{ pointerEvents: selecting ? 'none' : 'auto' }}>{box.number}</button></div>)}
          {selecting && hover && <div className="review-hover" style={{ top: hover.top, left: hover.left, width: hover.width, height: hover.height }} />}
        </div>
      </div>
    </main>
    <aside className="review-panel">
      <div className="review-tabs" role="tablist">
        <button type="button" role="tab" aria-selected={mode === 'points'} onClick={() => { setMode('points'); setHover(null) }}>確認ポイント</button>
        <button type="button" role="tab" aria-selected={mode === 'details'} onClick={() => { setMode('details'); setSelecting(false); setHover(null) }}>画面の詳細設計</button>
      </div>
      <button type="button" className="review-toggle" aria-pressed={showBoxes} onClick={() => mode === 'points' ? setShowPointBoxes(value => !value) : setShowDetailBoxes(value => !value)}>{mode === 'points' ? '確認ポイント' : '詳細設計'}の連番・枠を{showBoxes ? '非表示' : '表示'}</button>
      {mode === 'points' ? <>
        <p>判断したい項目を確認し、コメントまたは承認を入力してください。</p>
        {metadata.review_points.length === 0 && custom.length === 0 && <p className="review-empty">確認ポイントはまだありません。</p>}
        {[...metadata.review_points.map(point => ({ number: point.number, kind: 'point' as const, point })), ...custom.map(note => ({ number: note.number, kind: 'custom' as const, note }))].sort((a, b) => a.number - b.number).map(entry => entry.kind === 'point' ? (() => {
          const point = entry.point
          const item = items.find(value => value.number === point.number)!
          return <section key={`point-${point.number}`} className={`review-card ${item.approved ? 'approved' : item.reopened ? 'reopened' : ''}`}>
            <h2><span className={`review-card-number ${showPointBoxes ? '' : 'hidden'}`}>{point.number}</span>{point.title}</h2><p>{point.description}</p>
            {item.previously_approved && <small className="review-history">過去の承認: {point.approval_history?.length}件 · {item.reopened ? '再確認中' : '承認済み'}</small>}
            <label><input type="checkbox" checked={item.approved} onChange={event => setItems(previous => previous.map(value => value.number === point.number ? { ...value, approved: event.target.checked, reopened: value.status_at_render === 'reopened' || value.previously_approved && Boolean(value.comment) } : value))} />承認する</label>
            <textarea id={`point-feedback-${point.number}`} aria-label={`${point.title}へのコメント`} value={item.comment} onChange={event => setItems(previous => previous.map(value => value.number === point.number ? { ...value, comment: event.target.value, approved: event.target.value.trim() ? false : value.status_at_render === 'approved', reopened: value.previously_approved && Boolean(event.target.value.trim()) || value.status_at_render === 'reopened' } : value))} placeholder={item.previously_approved ? '追加の指摘' : '気になる点や変更案'} />
          </section>
        })() : (() => {
          const note = entry.note
          return <section key={`custom-${note.number}`} className="review-card custom"><h2><span className={`review-card-number ${showPointBoxes ? '' : 'hidden'}`}>{note.number}</span>選択要素への指摘</h2><p>{note.target.tag}「{note.target.text.slice(0, 48)}」</p>
            <label><input type="checkbox" checked={note.approved} onChange={event => setCustom(previous => previous.map(value => value.number === note.number ? { ...value, approved: event.target.checked } : value))} />承認する</label>
            <textarea id={`custom-feedback-${note.number}`} aria-label={`選択要素${note.number}へのコメント`} value={note.comment} onChange={event => setCustom(previous => previous.map(value => value.number === note.number ? { ...value, comment: event.target.value, approved: event.target.value.trim() ? false : value.approved } : value))} placeholder="この要素への指摘" />
            <button type="button" onClick={() => { customTargets.current.delete(note.number); setCustom(previous => previous.filter(value => value.number !== note.number)) }}>この指摘を削除</button>
          </section>
        })())}
        <button type="button" onClick={() => { setSelecting(value => !value); setHover(null) }}>{selecting ? '選択を終了' : '要素を選んで指摘'}</button>
      </> : <>
        <p>画面上の項目と動作を確認してください。</p>
        {metadata.screen_details.length === 0 && <p className="review-empty">画面の詳細設計は未入力です。</p>}
        {metadata.screen_details.map(detail => <section key={detail.key} className="review-card detail"><button type="button" className="review-detail-summary" aria-expanded={openDetail === detail.key} onClick={() => selectDetail(detail)}><span className={`review-card-number ${showDetailBoxes ? '' : 'hidden'}`}>{detail.number}</span><span>{detail.name}<small>{detail.region} / {detail.type} / {detail.description}</small></span></button>
          {openDetail === detail.key && <div><dl><dt>できること</dt><dd>{detail.capability}</dd><dt>処理種別</dt><dd>{behaviorLabels[detail.behavior] ?? detail.behavior}</dd><dt>きっかけ</dt><dd>{detail.trigger}</dd><dt>結果</dt><dd>{detail.result}</dd><dt>失敗時</dt><dd>{detail.failure}</dd></dl><textarea id={`detail-feedback-${detail.key}`} aria-label={`${detail.name}の詳細設計へのコメント`} value={detailComments[detail.key] ?? ''} onChange={event => setDetailComments(previous => ({ ...previous, [detail.key]: event.target.value }))} placeholder="詳細設計への指摘" /></div>}
        </section>)}
        {metadata.screen_details.length > 0 && <label><input type="checkbox" checked={detailsApproved} onChange={event => setDetailsApproved(event.target.checked)} />画面詳細設計を承認する</label>}
      </>}
      <label className="review-general">全体コメント<textarea value={generalComment} onChange={event => setGeneralComment(event.target.value)} /></label>
      <button type="button" className="review-submit" onClick={send}>フィードバックを送信</button><p role="status">{message}</p>
    </aside>
  </div>
}
