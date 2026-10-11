from pathlib import Path
import json, shutil, hashlib
O=Path(__file__).parent
S=Path('/Users/yukihito/Documents/github_projects/context/utils/skills/discovery/explain-html')
def save(p,v): (O/p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
shutil.copyfile(O.parents[1]/'prompt.txt',O/'source.txt')
def meta(title): return dict(title=title,locale='ja',visual_preset='editorial',quality_profile='showcase',animation='none')
def arch(title,nodes,edges):
 return dict(schema_version=1,diagram_type='architecture',meta=meta(title),components=[dict(id=i,label=l,type=t,pos=p,size=[190,76]) for i,l,t,p in nodes],connections=[dict(id='e'+str(k),from_=a,to=b,label=l) for k,(a,b,l) in enumerate(edges)])
def fix(m):
 for e in m.get('connections',[]): e['from']=e.pop('from_')
 return m
models={}
models['overview']=fix(arch('依頼の受付と画像変換は別の仕事',[
 ('client','クライアント','frontend',[60,110]),('server','サーバー','backend',[410,110]),('job','ジョブ記録','database',[410,360]),('worker','ワーカー','backend',[60,360])],[('client','server','POST・GET'),('server','job','作成・参照'),('worker','job','状態・結果を保存')]))
models['overview']['meta']['viewBox']=[700,540]
models['example']=dict(schema_version=1,diagram_type='sequence',meta={**meta('job_17 を受付から結果まで追う'), 'viewBox':[820,730],'column_fit':'spread'},participants=[dict(id=i,label=l,type=t) for i,l,t in [('client','クライアント','frontend'),('server','サーバー','backend'),('worker','ワーカー','backend')]],messages=[dict(id=i,**{'from':a,'to':b},y=y,label=l,variant=v) for i,a,b,y,l,v in [
 ('send','client','server',180,'① POST /jobs','emphasis'),('accepted','server','client',260,'② 202 + job_17','return'),('run','worker','worker',340,'③ queued → running','default'),('finish','worker','worker',420,'③ completed + resultUrl','default'),('query','client','server',510,'④ GET /jobs/job_17','emphasis'),('result','server','client',590,'④ completed + resultUrl','return')]])
models['api']=fix(arch('2つの操作と2つの識別子',[
 ('client','クライアント','frontend',[60,110]),('post','POST /jobs','backend',[420,110]),('get','GET /jobs/{jobId}','backend',[60,380]),('record','ジョブ記録','database',[420,380])],[('client','post','imageId + requestKey'),('post','record','同じキーは同じjobId'),('client','get','jobIdで照会'),('get','record','状態・結果を参照')]))
models['api']['meta']['viewBox']=[740,580]
models['states']=dict(schema_version=2,diagram_type='lifecycle',meta=meta('同じジョブの4つの状態'),subject=dict(label='画像変換ジョブ job_17',beginning='サーバーが初回受付でジョブを作る',ending='ワーカーが成功または失敗を保存するまで。保存後の寿命は未指定',coverage='partial'),lanes=[dict(id='job',label='サーバーが保持するジョブ状態')],initial=['queued'],terminal=['completed','failed'],states=[dict(id=i,kind='state',label=i,lane='job',col=c,row=r,description=d) for i,c,r,d in [('queued',0,0,'受付後、ワーカーの処理開始を待つ'),('running',1,0,'ワーカーが画像変換を処理している'),('completed',2,0,'ワーカーが成功とresultUrlを保存した'),('failed',2,1,'ワーカーが失敗とreasonを保存した')]],transitions=[dict(id=i,kind='transition',**{'from':a,'to':b},event=e) for i,a,b,e in [('start','queued','running','ワーカーが開始'),('success','running','completed','変換成功'),('failure','running','failed','変換失敗')]])
models['retry']=dict(schema_version=2,diagram_type='workflow',meta=meta('503の再送は最大2回'),lanes=[dict(id='client',label='クライアントが受付結果を判断する'),dict(id='accepted',label='202の場合'),dict(id='stop',label='503が続く場合',variant='exception')],mainPath=['post','response','count','unknown'],nodes=[dict(id=i,lane=l,col=c,type=t,label=n,sublabel=sub) for i,l,c,t,n,sub in [('post','client',0,'frontend','POSTを送る','同じrequestKey'),('response','client',1,'frontend','応答を確認','202 / 503'),('count','client',2,'frontend','再送回数を確認','上限2回'),('known','accepted',1,'frontend','jobIdを使いGET','202は受付'),('unknown','stop',3,'frontend','受付結果不明','再送を止める')]],edges=[dict(id=i,**{'from':a,'to':b},label=l,role=r) for i,a,b,l,r in [('sent','post','response','サーバーの応答','main'),('ok','response','known','202','branch'),('busy','response','count','503','main'),('again','count','post','再送回数 < 2','return'),('exhausted','count','unknown','再送回数 = 2','error')]])
models['sources']=fix(arch('原文から説明と確認記録へ',[
 ('source','架空仕様の原文','external',[60,110]),('content','本文・図・通信例','frontend',[410,110]),('coverage','項目対応表','database',[410,350]),('review','静的検査・内容レビュー','backend',[60,350])],[('source','content','意味を保持'),('source','review','原文と照合'),('content','coverage','説明先を記録'),('review','coverage','欠落を確認')]))
models['sources']['meta']['viewBox']=[700,540]
plans=[]
qs={'overview':('誰が何を担当するか','architecture','担当と保存の関係を示す'),'example':('受付と完了はいつ分かるか','sequence','呼出しと応答を時間順に示す'),'api':('requestKeyとjobIdはどう使うか','architecture','操作と識別子と記録の対応を示す'),'states':('ジョブの状態は何が変えるか','lifecycle','同じジョブの可能な変化を示す'),'retry':('503ならどこまで再送するか','workflow','条件分岐と停止と戻り経路を示す'),'sources':('説明の根拠と検証範囲は何か','architecture','資料と説明と記録の対応を示す')}
for pid,m in models.items():
 save('diagrams/'+pid+'.json',m)
 q,t,r=qs[pid];plans.append(dict(id=pid,page_id=pid,role='overview',question=q,takeaway=r,type=t,selection_reason=r,scope='依頼の架空仕様に限定',sources=['source.txt'],entities=m.get('components',m.get('participants',m.get('states',m.get('nodes')))),relations=m.get('connections',m.get('messages',m.get('transitions',m.get('edges')))),parent_diagram_id=None,model_path='diagrams/'+pid+'.json',target_ids=[pid+'-detail']))
save('diagram-plan.json',dict(diagrams=plans))
