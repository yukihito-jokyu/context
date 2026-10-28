// 説明用のインメモリ模擬実装。実APIへの通信ではない。
// 再送応答の202は模擬実装の仮定。原文は再送時のHTTP状態を指定しない。
const jobs = new Map();
let nextId = 17;
function post({imageId,requestKey}) {
  if (!jobs.has(requestKey)) jobs.set(requestKey,{jobId:`job_${nextId++}`,imageId,status:'queued'});
  return {status:202,body:{jobId:jobs.get(requestKey).jobId}};
}
function get(jobId) { return {...[...jobs.values()].find(j=>j.jobId===jobId)}; }
function run(jobId,success) {
 const job=[...jobs.values()].find(j=>j.jobId===jobId);
 job.status='running';
 const running=get(jobId);
 if(success){job.status='completed';job.resultUrl='https://example.invalid/results/job_17.png';}
 else {job.status='failed';job.reason='画像を変換できませんでした';}
 return {running,terminal:get(jobId)};
}
function retry(statuses,requestKey='req_A') {
 const sent=[];
 for(let i=0;i<3;i++){
  const status=statuses[i];sent.push({attempt:i+1,requestKey,status});
  if(status===202)return {sent,display:'受付済み。job_17の状態を取得する'};
  if(status!==503)throw new Error('この模擬例が扱わない応答');
 }
 return {sent,display:'受付結果不明'};
}
const input={imageId:'img_42',requestKey:'req_A'};
const first=post(input),duplicate=post(input),queued=get('job_17');
const success=run('job_17',true);
jobs.clear();nextId=17;post(input);const failure=run('job_17',false);
const result={notice:'提供された架空仕様の理解を助ける模擬実装であり、実サーバー、永続化、排他制御の実装保証ではない。',input,first,duplicate,queued,success,failure,retries:[[202],[503,202],[503,503,202],[503,503,503]].map(s=>retry(s)),unspecified:['再送時のHTTP応答状態','キーの有効期間','同じキーで異なる画像IDの場合','並行POSTの排他','GETの間隔','503の待ち時間・バックオフ','POST以外のエラー応答']};
require('node:fs').writeFileSync(require('node:path').join(__dirname,'simulation-results.json'),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({first:first.body.jobId,duplicate:duplicate.body.jobId,queued:queued.status,completed:success.terminal.status,failed:failure.terminal.status,retryCounts:result.retries.map(r=>r.sent.length)}));
