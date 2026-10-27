from pathlib import Path
import json
root=Path(__file__).parent; p=root/'project'
def e(path,start,end):
    return {'path':path,'start':start,'end':end,'quote':'\n'.join((p/path).read_text().splitlines()[start-1:end])}
def a(name,type,path,start,end): return {'name':name,'type':type,'evidence':[e(path,start,end)]}
s='subscriptions/model.ts'; b='billing/invoice.ts'
def c(path,symbol,kind,description,attrs,start,end):
    return {'key':path+'::'+symbol,'symbol':symbol,'name':symbol,'domain':str(Path(path).parent),'kind':kind,'description':description,'attributes':attrs,'evidence':[e(path,start,end)]}
def r(source,target,member,path,start,end):
    return {'source':source,'target':target,'kind':'association','member':member,'source_multiplicity':None,'target_multiplicity':'1','evidence':[e(path,start,end)]}
m={'schema_version':1,'title':'定期契約と請求のドメインモデル','domains':[
    {'path':'billing','name':'billing','description':'請求対象の契約と請求額を保持するコードの配置領域。'},
    {'path':'subscriptions','name':'subscriptions','description':'顧客、定期契約、料金プランの選択肢を定義するコードの配置領域。'}],
    'concepts':[
        c(s,'Plan','enum','定期契約の料金プランを monthly または annual から選ぶ文字列の選択型。',[],1,1),
        c(s,'Customer','concept','顧客の識別子と変更可能な表示名を保持する。識別子は読み取り専用で、同一性の判定規則は宣言されていない。',[a('customerId','string',s,4,4),a('displayName','string',s,4,4)],3,5),
        c(s,'Subscription','concept','定期契約の識別子を保持し、必須の顧客と料金プランを参照する。',[a('subscriptionId','string',s,9,9)],7,13),
        c(b,'Invoice','concept','請求書の識別子と円建ての請求額を保持し、請求対象となる契約を必須で参照する。',[a('invoiceId','string',b,5,5),a('amountYen','number',b,7,7)],3,9)
    ],'relations':[
        r(b+'::Invoice',s+'::Subscription','subscription',b,6,6),
        r(s+'::Subscription',s+'::Customer','customer',s,10,10),
        r(s+'::Subscription',s+'::Plan','plan',s,11,11)
    ],'questions':'Customer・Subscription・InvoiceにはEntity基底型やentity注釈がないためconceptにした。業務上の同一性をどの規則で判定するかは未確認。\n参照先の多重度1は必須の単一プロパティ宣言に基づく。顧客ごとの契約数、契約ごとの請求書数、プランごとの契約数を制限するコードはなく、逆方向の多重度は未確認。\nreadonlyはプロパティの再代入を制限するが、参照先の寿命を所有する根拠にはならない。顧客・契約・請求書の削除や生成を連動させる規則は未確認。\n領域は宣言元の親ディレクトリによる配置単位であり、業務上の境界として妥当かは未確認。','unread':[]}
output=p/'.skill-runs/generate-domain-model-from-code/out/subscription-billing/model.json'
output.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
read={'inventory_files_read':[b,s],'background_files_read':['README.md'],'root_agents_exists':(p/'AGENTS.md').exists(),'unread':[],'concepts':4,'relations':3,'classification_review':'Planはリテラル選択型、他のクラスは基底型・注釈がないためconcept。','relation_review':'必須の単一参照3本をassociationとして表し、target_multiplicityは1、逆方向はnull。所有や集約の宣言はない。','new_model_created_by':'/root/renamed_catalog_sample','reused_previous_models':False}
(root/'evidence/semantic-review.json').write_text(json.dumps(read,ensure_ascii=False,indent=2)+'\n')
print('model.json: 4 concepts, 3 relations, 2 domains, no unread files')
