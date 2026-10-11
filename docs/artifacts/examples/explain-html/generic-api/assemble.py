from pathlib import Path
import json,html,base64,hashlib,xml.etree.ElementTree as E
O=Path(__file__).parent
esc=html.escape

def code(title,text,ident,stage=None):
 (O/(ident+'.txt')).write_text(text+'\n')
 lines=''.join(f'<span class="code-line" id="{ident}-l{k}" tabindex="-1"><span class="line-number" data-line="{k}" aria-hidden="true"></span><code>{esc(line)}</code></span>' for k,line in enumerate(text.splitlines(),1))
 return f'<div class="code-panel"'+(f' data-flow-stage="{stage}"' if stage else '')+f'><div class="code-heading">{title}</div><pre class="code-lines">{lines}</pre></div>'
def para(t):return '<p>'+t+'</p>'
def prose(t):return '<div class="prose">'+t+'</div>'
def section(id,title,t):return f'<div class="prose" id="{id}" tabindex="-1"><h3>{title}</h3>{t}</div>'
def ref():return '<a href="#source-spec">根拠：架空仕様の原文</a>'
links={
 'overview':{'client':'api-detail','server':'identity','job':'states-detail','worker':'states-detail'},
 'example':{'client':'example-detail','server':'acceptance-example','record':'worker-example','worker':'worker-example'},
 'api':{'client':'identity','post':'post-detail','get':'get-detail','record':'identity'},
 'states':{k:'state-'+k for k in ['queued','running','completed','failed']},
 'retry':{'post':'retry-detail','response':'retry-detail','count':'attempts','known':'get-detail','unknown':'unknown-detail'},
 'sources':{'source':'source-spec','content':'assumptions','coverage':'coverage-detail','review':'verification-detail'}}
alt={
'overview':'クライアントはサーバーにPOSTとGETを送り、サーバーはジョブ記録を作成・参照し、ワーカーはジョブ状態と結果を保存する。',
'example':'クライアントのPOSTにサーバーは202とjob_17を返す。その後ワーカーがrunningとcompletedを保存し、GETにサーバーが結果を返す。',
'api':'クライアントはPOSTにimageIdとrequestKey、GETにjobIdを使う。サーバーは同じキーを同じジョブへ対応させ、状態を照会する。',
'states':'queuedからワーカーの開始でrunningへ移る。変換成功ならcompleted、失敗ならfailedへ分岐する。',
'retry':'クライアントはPOSTの202ならGETへ進む。503なら再送回数を確認し、2回未満なら同じキーで再送し、2回なら受付結果不明で停止する。',
'sources':'保存した架空原文から本文と図を作り、項目対応表と静的検査・内容レビューで原文との一致を確認する。'}
read={
'overview':'線は担当間の関係を示します。サーバーの受付応答と、ワーカーの画像変換は別の動作です。ジョブ記録は保存内容の概念であり、実在するDB製品や配置は仮定しません。',
'example':'上から下へ、1件の成功例を追います。①の入力は imageId=img_42、requestKey=req_img42_01 です。③はワーカーによる保存を表し、クライアントへの完了通知ではありません。GETのタイミングはこの例の仮定です。',
'api':'上段のPOSTは受付、左下のGETは照会です。線は操作と入力・保存対象の関係を示し、4つの箱を時間順に実行する図ではありません。',
'states':'線は同じ job_17 が取り得る変化を示します。queuedとrunningは処理の途中で、completedとfailedはこの仕様で描く処理の終点です。ジョブ記録の削除時点は原文にありません。',
'retry':'503の経路では、クライアントが再送した回数を数えます。初回は再送0回です。202の経路はjobIdでの照会へ進み、上限到達の経路は「受付結果不明」で止まります。',
'sources':'線は根拠と成果物の対応を示します。原文が架空仕様を定義し、本文は原文を説明します。検査の通過だけで実APIの存在やブラウザ動作を証明する図ではありません。'}

def overview(pid):
 raw=(O/'diagrams'/f'{pid}.svg').read_bytes();root=E.fromstring(raw);vb=list(map(float,root.attrib['viewBox'].split()));W,H=vb[2:];sha=hashlib.sha256((O/'diagrams'/f'{pid}.json').read_bytes()).hexdigest()
 uri='data:image/svg+xml;base64,'+base64.b64encode(raw).decode();hot='';rects={}
 for g in root.iter():
  nid=g.attrib.get('data-node-id')
  if nid:
   r=next(x for x in g if x.tag.endswith('rect'));a=r.attrib;rects[nid]=a
   x,y,w,h=[float(a[k]) for k in ['x','y','width','height']]
   hot+=f'<a class="diagram-hotspot" href="#{links[pid][nid]}" aria-label="{esc(g.attrib["data-node-label"])}の説明へ" style="left:{x/W*100}%;top:{y/H*100}%;width:{w/W*100}%;height:{h/H*100}%"></a>'
 flow='';controls='';attrs=''
 if pid=='example':
  attrs=' data-flow-diagram'
  stages=[('1','クライアントが画像IDとキーを送る','send',['client']),('2','サーバーが202とjob_17を返す','accepted',['server']),('3','ワーカーが状態と成功結果を保存する','run finish',['worker','record']),('4','クライアントがGETし結果を表示する','query result',['client','server'])]
  traces=''
  for p in root.iter():
   eid=p.attrib.get('data-composition-edge-id')
   if p.tag.endswith('path') and eid:traces+=f'<path class="trace-signal" data-flow-edge="{eid}" d="{p.attrib["d"]}" pathLength="1" aria-hidden="true"/>'
  highlights=''
  for stage,caption,edges,nodes in stages:
   for nid in nodes:
    a=rects[nid];highlights+=f'<rect class="stage-highlight" data-flow-stage="{stage}" x="{a["x"]}" y="{a["y"]}" width="{a["width"]}" height="{a["height"]}" rx="6"/>'
  flow=f'<svg class="trace-svg" viewBox="{root.attrib["viewBox"]}" aria-hidden="true">{traces}{highlights}</svg>'
  controls='<div class="flow-controls" hidden><button type="button" data-flow-action="play">再生</button><button type="button" data-flow-action="pause">一時停止</button><button type="button" data-flow-action="reset">全体を表示</button>'
  controls+=''.join(f'<button type="button" data-flow-select="{st}" data-flow-caption="{cap}" data-flow-edges="{edges}">段階{st}</button>' for st,cap,edges,nodes in stages)+'</div><p class="flow-status" aria-live="polite">全体表示：①受付依頼 → ②受付応答 → ③処理 → ④結果照会</p><p class="flow-note">再生は説明用の速度です。待ち時間や変換性能を示しません。</p>'
 return f'<div class="concern-whole-map" data-concern-overview="{pid}"><figure{attrs}><div class="archify-overview-image"><img class="whole-map-image" alt="{esc(alt[pid])}" src="{uri}" data-archify-model-sha256="{sha}" data-archify-preset="editorial" data-archify-export="canonical-svg-offline-adapter"/>{hot}{flow}</div><figcaption>{read[pid]} {ref()}</figcaption>{controls}</figure><div class="diagram-links"><a href="#{pid}-detail">この図の詳細へ</a><a href="diagrams/{pid}.svg">原図SVG</a></div></div>'
P=[]
def add(pid,label,intro,body):P.append(dict(id=pid,label=label,group='learn',intro_html=prose(intro),overview_html=overview(pid),body_html=body))
add('overview','全体像',para('<span class="lead">202で受付を知り、GETで処理の結末を知る。</span>')+para('この架空APIでは、利用者が画像変換を依頼し、クライアントがサーバーへ通信します。非同期とは、サーバーが受付応答を返した後に、ワーカーが変換処理を進められる仕組みです。'),section('overview-detail','受付と完了を分けて考える',para('サーバーは初回のPOSTで job_17 を作り、202とjobIdを返します。クライアントはjobIdを受け取った段階では画像を表示せず、GETでジョブの状態を取得します。')+para('ワーカーが変換に成功すると、ワーカーは completed と resultUrl を保存します。クライアントはGETで completed を確認した後に結果を表示します。ワーカーが失敗を保存した場合、クライアントは failed に対応するreasonを表示します。')+para('同じ依頼を再送するとき、クライアントは同じrequestKeyを使います。サーバーは重複ジョブを作らず、元のjobIdを返します。')+para(ref()))+prose('<p class="note">POSTの202は画像変換の完了を意味しません。503が続く場合の「受付結果不明」も、ジョブのfailedとは別です。</p>'))
request='POST /jobs\n\n{"imageId":"img_42","requestKey":"req_img42_01"}'
accepted='202\n\n{"jobId":"job_17"}'
get='GET /jobs/job_17\n\n{"jobId":"job_17","status":"completed",\n "resultUrl":"https://example.invalid/results/job_17.png"}'
add('example','具体例の動き',para('利用者が img_42 の画像変換を依頼した1回の成功例です。クライアントは req_img42_01 を同じ依頼の識別子として保持し、サーバーから受け取った job_17 を照会に使います。'),section('example-detail','① クライアントが受付を依頼する',para('以下はHTTP風の通信例です。JSONの形式、画像IDのキー名imageId、状態のキー名status、具体的な値とURLは説明用の仮定です。実行可能なAPI接続コードではありません。'))+code('① クライアント → サーバー｜受付依頼',request,'post-request','1')+section('acceptance-example','② サーバーが受付を返す',para('サーバーは初回の依頼を受け付け、job_17を作ります。202とjobIdを受け取ったクライアントは、結果取得のためにjobIdを保持します。202の応答には変換完了を読み込みません。'))+code('② サーバー → クライアント｜受付応答',accepted,'post-accepted','2')+section('worker-example','③ ワーカーがジョブを処理する',para('ワーカーはqueuedのjob_17をrunningに移し、画像を変換します。この成功例では、ワーカーがcompletedとresultUrlを保存します。ワーカーはPOSTの202を待つという仕様ではなく、この図は受付後に処理する例を示しています。'))+code('③ 保存状態の説明用記録｜HTTP通信ではない','job_17: queued\njob_17: running\njob_17: completed + resultUrl','worker-record','3')+section('result-example','④ クライアントが結果を照会する',para('クライアントはGET /jobs/job_17で状態を取得します。この例では照会時に変換が完了しているため、クライアントはresultUrlの結果を表示します。GETのHTTP応答コードは原文に指定されていないため、この通信例では補いません。'))+code('④ クライアント → サーバー → クライアント｜結果照会',get,'get-result','4')+prose(para('図の④と通信例のGETは同じjob_17を対象にします。まだqueuedまたはrunningなら、クライアントは完了結果を表示できません。照会間隔や待機上限は<a href="#unspecified">未指定事項</a>です。 '+ref())))
add('api','操作と識別子',para('クライアントはPOSTで仕事を依頼し、GETで仕事の状態を照会します。requestKeyは同じ依頼の再送を識別し、jobIdはサーバーが作ったジョブを識別します。'),section('api-detail','依頼とジョブを結び付ける',para('開発者は、同じ依頼を再送する経路でrequestKeyを引き継ぎます。サーバーからjobIdが返った後、クライアントはGETのパスへjobIdを入れます。requestKeyをGETのジョブIDとして使うことは、この仕様にありません。'))+section('post-detail','POST /jobs：受付の操作',para('クライアントは画像IDとrequestKeyを送ります。サーバーは初回にjob_17を作り、202とjobIdを返します。同じrequestKeyが再送されると、サーバーはジョブを増やさず同じjobIdを返します。再送時のHTTP応答コードは原文にありません。'))+code('同じ依頼の再送｜キーと返るjobIdを確認','再送入力: {"imageId":"img_42","requestKey":"req_img42_01"}\n返る内容: {"jobId":"job_17"}\nジョブ数: この再送では増えない','same-request')+section('identity','requestKeyとjobIdの役割',para('requestKeyはクライアントが再送に使う値で、jobIdはサーバーから返る値です。同じrequestKeyに対してサーバーが同じjobIdを返すため、クライアントが再送しても同じ仕事を追えます。この性質を、同じ操作を繰り返してもジョブが重複しないという意味で「冪等性」と呼びます。')+para('原文はrequestKeyの生成形式、保存期間、利用者間の共有範囲を定義していません。同じキーで画像IDを変えた場合の扱いも定義していないため、開発者はその動作を推測して実装しません。'))+section('get-detail','GET /jobs/job_17：照会の操作',para('クライアントはjobIdで状態を取得します。completedならクライアントはresultUrlの結果を表示し、failedならreasonを表示します。queuedまたはrunningは処理途中を示します。クライアントが照会で得る状態は、その時点の状態であり、全状態を順に観測できるとは限りません。')+para(ref())))
add('states','ジョブの状態',para('状態はサーバー側のジョブ記録が保持する状況です。ワーカーが状態を進め、クライアントはGETで状態を読みます。POSTのHTTPコードはジョブ状態の名前ではありません。'),section('states-detail','誰が状態を変えるか',para('サーバーが初回受付で作ったジョブを、ワーカーがqueuedからrunningへ移します。ワーカーが変換の結末を保存することで、クライアントは後のGETで成功または失敗を判断できます。'))+''.join(section('state-'+s,s+'：'+label,para(t)) for s,label,t in [
('queued','処理開始待ち','ジョブは受付後にワーカーの処理開始を待ちます。クライアントはqueuedを取得しても、画像変換が完了したとは扱いません。'),
('running','変換中','ワーカーが画像変換を進めています。クライアントはrunningを取得しても、resultUrlの結果を表示する条件を満たしていません。'),
('completed','変換成功','ワーカーは変換に成功したとき、completedとresultUrlを保存します。クライアントはcompletedを取得したときに結果を表示します。'),
('failed','変換失敗','ワーカーは変換に失敗したとき、failedとreasonを保存します。クライアントはfailedを取得したときに理由を表示します。failedのジョブを再実行する操作は原文に定義されていません。')])+code('失敗時のGET｜JSON表現と理由の値は説明用の仮定','GET /jobs/job_17\n\n{"jobId":"job_17","status":"failed",\n "reason":"画像を変換できませんでした"}','get-failed')+prose(para('成功の保存内容はresultUrl、失敗の保存内容はreasonです。図の分岐はどちらかの結末を表し、失敗後に自動で成功へ進む矢印はありません。 '+ref())))
add('retry','条件と503',para('クライアントがPOSTの503を受け取った場合、クライアントは同じrequestKeyで最大2回再試行します。再試行後も503なら、クライアントは「受付結果不明」と表示します。'),section('retry-detail','503は受付の再試行条件',para('初回の503を受け取ったクライアントは、元の画像IDとrequestKeyを保持して再送します。再送で202を受け取った場合、クライアントはjobIdを使った状態取得へ進みます。この202も変換完了ではありません。')+para('最大2回は、初回の送信とは別に許す再試行回数です。したがって、503が続く経路では送信を合計3回行います。この規則はPOSTの503に対するものであり、GETの再試行規則や他のHTTPコードの規則へ拡張しません。'))+section('attempts','503が3回続いた具体例',para('以下の全送信で、クライアントは同じreq_img42_01を使います。再送回数が2に達した後、クライアントはさらに4回目を送らず、受付結果不明を表示します。'))+code('初回＋再試行2回｜説明用通信ログ','初回送信    requestKey=req_img42_01 → 503\n再試行1回目 requestKey=req_img42_01 → 503\n再試行2回目 requestKey=req_img42_01 → 503\n表示: 受付結果不明\n以後: この再試行手順を停止','retry-log')+section('unknown-detail','受付結果不明とfailedを区別する',para('受付結果不明は、クライアントがこの手順では受付の結末を確定できなかったという表示です。クライアントは、503だけを根拠に「ジョブが存在しない」や「変換に失敗した」と断定しません。failedはワーカーが保存するジョブ状態であり、クライアントはGETでfailedを取得した場合に理由を表示します。')+para('原文は、受付結果不明の後にrequestKeyからジョブを探す操作を定義していません。クライアントがjobIdを持っていない場合にGET /jobs/job_17へ進めると仮定しません。')+para(ref()))+section('unspecified','この架空仕様にない条件',para('原文は認証、変換形式、タイムアウト、GETの照会間隔と待機上限、503以外のエラー、同時受付の内部制御を定義していません。原文はrequestKeyの保存期限と競合時の応答、jobId不存在時の応答、ジョブ記録とresultUrlの寿命も定義していません。')+para('この解説は未指定の条件を実在するAPI契約として補いません。開発者が実装を作る段階では、開発者と仕様の管理者が未指定事項を決める必要があります。')))
raw=(O/'source.txt').read_text()
add('sources','資料と確認範囲',para('根拠は利用者から渡された架空APIの原文1件です。確認日は2026年10月11日です。この解説は、実在する製品・サービスの公式API資料ではありません。'),section('sources-detail','原文と説明用の仮定を分ける',para('原文で確認できる動作は、受付、重複防止、ワーカーの状態保存、GETによる表示条件、503の再試行上限です。通信例のJSON表現や具体値は、動作を理解するために追加した仮定です。'))+section('source-spec','保存した原文',f'<blockquote>{esc(raw)}</blockquote>'+para('<a href="source.txt">原文テキストを開く</a>。単体HTMLでも原文を確認できるよう、上に全文を保存しています。'))+section('assumptions','説明用の仮定と資料からの解釈',para('説明用の仮定：画像IDをimageId、状態をstatusというJSONキーで表すこと、img_42とreq_img42_01という値、example.invalidの結果URL、失敗理由の文面、成功後の照会タイミングです。ワーカーとジョブ記録の線は保存操作の概念表現です。DB製品やキューの内部実装は決めていません。')+para('資料からの解釈：最大2回の再試行は初回に追加する2回です。queuedまたはrunningを取得した時点では、completedの結果表示条件はまだ成立しません。HTTP風の通信例は、このAPIを実行するコードではありません。'))+section('coverage-detail','原文の項目を逆照合した対応表',para('原文の各動作・識別子・条件を<a href="coverage.json">項目対応表JSON</a>へ記録しました。説明先の存在は機械検査で確認し、主体・条件・結果の一致は内容レビューで確認しました。'))+section('verification-detail','検証できた範囲',para('同梱Archify 2.16.0で6モデルのshowcase検証と配布を実行し、標準serializeSvgを使うオフライン補助処理でSVGを取得しました。画像は全viewBox、背景、グリッド、凡例、文字、記号を保持しています。')+para('ブラウザは禁止されているため、ブラウザでの表示、狭い画面の見え方、戻る・進む、フォーカス移動、再生操作、印刷を実操作で確認していません。SVGの補助出力をブラウザ操作や標準PNGとの一致確認として扱いません。')+para('<a href="records/verification.json">機械検査の記録</a>と<a href="records/content-review.md">内容レビューの記録</a>を保存しました。')))
model=dict(title='画像変換の非同期APIを理解する',scope='架空仕様のみ｜初めて使う開発者向け｜202・重複防止・状態・503再試行｜確認日 2026-10-11',groups={'learn':'理解する'},pages=P)
(O/'page-model.json').write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n')
items=[]
for key,topic,target in [
('fiction','架空APIであること','sources-detail'),('image','利用者が画像変換を依頼する','example-detail'),('post','POST /jobsに画像IDとrequestKeyを送る','post-detail'),('key','同じ依頼の再送で同じrequestKey','identity'),('first','初回にjob_17作成と202とjobId','acceptance-example'),('dedupe','同じキーで重複を作らず同じjobId','identity'),('queued','queuedの処理開始待ち','state-queued'),('running','ワーカーがrunningへ移す','state-running'),('completed','成功時completedとresultUrl保存','state-completed'),('failed','失敗時failedとreason保存','state-failed'),('get','GET /jobs/job_17で状態取得','get-detail'),('show-result','completedなら結果表示','result-example'),('show-reason','failedなら理由表示','state-failed'),('accepted-only','202は完了ではない','overview-detail'),('503','503なら同じrequestKeyで最大2回再試行','retry-detail'),('unknown','なお503なら受付結果不明','unknown-detail')]:
 items.append(dict(key=key,topic=topic,source_url='source.txt',target_id=target,status='explained'))
(O/'coverage.json').write_text(json.dumps(dict(scope='2026-10-11に提供された架空API原文の全条件。未指定のAPI契約は補わない。',sources=[dict(url='source.txt',title='利用者が提供した架空API仕様')],items=items),ensure_ascii=False,indent=2)+'\n')
