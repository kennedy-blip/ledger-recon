const $=id=>document.getElementById(id);
const state={internal:[],gateway:[],rows:[],audit:[],summary:null,filter:"ALL",api:false};
const money=(v,c="KES")=>v==null?"—":new Intl.NumberFormat("en-KE",{style:"currency",currency:c,minimumFractionDigits:2}).format(v);
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function toast(s){$("toast").textContent=s;$("toast").classList.remove("hidden");setTimeout(()=>$("toast").classList.add("hidden"),2500)}
async function api(url,opt={}){const r=await fetch(url,{...opt,headers:{"Content-Type":"application/json",...(opt.headers||{})}});const d=await r.json();if(!r.ok)throw Error(d.error||"API request failed");return d}
function editors(){const a=JSON.parse($("internal-json").value),b=JSON.parse($("gateway-json").value);if(!Array.isArray(a)||!Array.isArray(b))throw Error("Editors must contain JSON arrays.");return [a,b]}
function fallback(a,b,t){
 const groups={};b.forEach((g,i)=>(groups[g.referenceId]??=[]).push({...g,_i:i}));
 const counts={};a.forEach(x=>counts[x.referenceId]=(counts[x.referenceId]||0)+1);
 const seen=new Set(),rows=[];let matched=0,delta=0;
 function add(ref,type,i,g,d,c){rows.push({referenceId:ref,type,internalAmount:i?.amount??null,gatewayAmount:g?.amount??null,diff:d,currency:c,status:type==="MATCHED"?"MATCHED":"OPEN",exceptionId:null})}
 a.forEach(i=>{const gs=groups[i.referenceId]||[];if(counts[i.referenceId]>1||gs.length>1){add(i.referenceId,"DUPLICATE_REF",i,gs[0],0,i.currency);gs.forEach(g=>seen.add(g._i));return}if(!gs.length){add(i.referenceId,"MISSING_IN_GATEWAY",i,null,-i.amount,i.currency);delta-=i.amount;return}const g=gs[0];seen.add(g._i);const d=Number((g.amount-i.amount).toFixed(4));if(g.currency===i.currency&&Math.abs(d)<=t){add(i.referenceId,"MATCHED",i,g,d,i.currency);matched+=Math.min(i.amount,g.amount)}else{add(i.referenceId,"AMOUNT_MISMATCH",i,g,d,i.currency);delta+=d}});
 b.forEach((g,i)=>{if(!seen.has(i)&&!counts[g.referenceId]){add(g.referenceId,"UNMATCHED_GATEWAY",null,g,g.amount,g.currency);delta+=g.amount}});
 const byType={};rows.forEach(r=>byType[r.type]=(byType[r.type]||0)+1);
 return {rows,audit:[],totals:{matched:byType.MATCHED||0,exceptions:rows.length-(byType.MATCHED||0),matchedValue:matched,unmatchedDeltaValue:delta,byType}}
}
function render(){
 const rows=state.filter==="ALL"?state.rows:state.rows.filter(r=>r.type===state.filter);
 $("results-body").innerHTML=rows.length?rows.map(r=>"<tr><td class='ref'>"+esc(r.referenceId)+"</td><td class='mono'>"+money(r.internalAmount,r.currency)+"</td><td class='mono'>"+money(r.gatewayAmount,r.currency)+"</td><td class='mono'>"+money(r.diff,r.currency)+"</td><td><span class='status "+esc(r.type)+"'>"+esc(r.type)+"</span></td><td><span class='status "+esc(r.status)+"'>"+esc(r.status)+"</span></td><td>"+(r.type==="MATCHED"?"—":r.status==="RESOLVED"?"Signed off":"<button class='btn' data-id='"+(r.exceptionId||"")+"' data-ref='"+esc(r.referenceId)+"'>Mark resolved</button>")+"</td></tr>").join(""):"<tr><td colspan='7' class='empty'>No records in this filter.</td></tr>";
 const t=state.summary?.totals||{};$("matched-count").textContent=t.matched??"—";$("matched-value").textContent="Matched value "+money(t.matchedValue||0);$("exception-count").textContent=t.exceptions??"—";$("variance-value").textContent=money(t.unmatchedDeltaValue||0);$("duplicate-count").textContent=t.byType?.DUPLICATE_REF||0;
 $("audit-list").innerHTML=state.audit.length?state.audit.map(x=>"<div class='flex justify-between border-b border-slate-800 pb-3'><div><div class='ref'>"+esc(x.referenceId)+"</div><div class='text-xs muted'>"+esc(x.type)+" · "+esc(x.resolutionNote||"")+"</div></div><span class='status "+esc(x.status)+"'>"+esc(x.status)+"</span></div>").join(""):"<div class='empty'>No audit events yet.</div>";
}
function editorsOut(){$("internal-json").value=JSON.stringify(state.internal,null,2);$("gateway-json").value=JSON.stringify(state.gateway,null,2);$("internal-total").textContent=state.internal.length+" ROWS";$("gateway-total").textContent=state.gateway.length+" ROWS"}
async function load(){
 try{const d=await api("/api/batches");state.api=true;state.internal=d.internalRows;state.gateway=d.gatewayRows;$("engine-status").textContent="LedgerRecon SQLite Engine: Active • Reference & Amount Matcher Ready";$("api-mode").textContent="PYTHON API"}
 catch(e){state.api=false;state.internal=[{referenceId:"TXN-90412",amount:1450,currency:"KES",status:"POSTED"},{referenceId:"TXN-90413",amount:820,currency:"KES",status:"POSTED"},{referenceId:"TXN-90414",amount:2500,currency:"KES",status:"POSTED"},{referenceId:"TXN-90415",amount:640,currency:"KES",status:"POSTED"}];state.gateway=[{referenceId:"TXN-90412",amount:1450,currency:"KES",status:"SETTLED"},{referenceId:"TXN-90413",amount:819.5,currency:"KES",status:"SETTLED"},{referenceId:"TXN-90415",amount:640,currency:"KES",status:"SETTLED"},{referenceId:"GW-UNMAPPED-77",amount:1220,currency:"KES",status:"SETTLED"}];$("engine-status").textContent="Offline demo mode · browser fallback active";$("api-mode").textContent="LOCAL FALLBACK"}
 editorsOut();$("diag-tolerance").textContent=$("tolerance").value+" KES"
}
async function run(){
 try{const [a,b]=editors(),t=Number($("tolerance").value);if(!Number.isFinite(t)||t<0)throw Error("Tolerance must be non-negative.");state.internal=a;state.gateway=b;let d;
 if(state.api){await api("/api/batches",{method:"POST",body:JSON.stringify({internalRows:a,gatewayRows:b})});d=await api("/api/reconcile",{method:"POST",body:JSON.stringify({amountTolerance:t})})}else d=fallback(a,b,t);
 state.rows=d.rows;state.audit=d.audit||[];state.summary=d;render();$("diag-tolerance").textContent=t+" KES";toast("Reconciliation complete · "+d.totals.matched+" matched / "+d.totals.exceptions+" exceptions")
 }catch(e){toast(e.message)}
}
$("run-btn").addEventListener("click",run);
$("filters").addEventListener("click",e=>{const b=e.target.closest("[data-filter]");if(!b)return;state.filter=b.dataset.filter;document.querySelectorAll(".tab").forEach(x=>x.classList.toggle("active",x===b));render()});
$("results-body").addEventListener("click",async e=>{const b=e.target.closest("[data-id]");if(!b)return;const note=prompt("Resolution note (optional):")||"";try{if(state.api&&b.dataset.id)await api("/api/reconcile",{method:"POST",body:JSON.stringify({action:"resolve",exceptionId:Number(b.dataset.id),resolutionNote:note})});const r=state.rows.find(x=>x.referenceId===b.dataset.ref&&x.type!=="MATCHED"&&x.status!=="RESOLVED");if(r){r.status="RESOLVED";state.audit.unshift({referenceId:r.referenceId,type:r.type,status:"RESOLVED",resolutionNote:note});render();toast("Exception marked resolved")}}catch(err){toast(err.message)}});
$("inject-btn").addEventListener("click",()=>{try{const [a,b]=editors();a.push({referenceId:"TXN-DUP-001",amount:1000,currency:"KES",status:"POSTED"});b.push({referenceId:"TXN-DUP-001",amount:1000,currency:"KES",status:"SETTLED"},{referenceId:"TXN-DUP-001",amount:995,currency:"KES",status:"SETTLED"},{referenceId:"TXN-GAP-002",amount:700,currency:"KES",status:"POSTED"});state.internal=a;state.gateway=b;editorsOut();run()}catch(e){toast(e.message)}});
$("reset-btn").addEventListener("click",async()=>{try{if(state.api){const d=await api("/api/batches",{method:"POST",body:JSON.stringify({reset:true})});state.internal=d.internalRows;state.gateway=d.gatewayRows}else await load();editorsOut();state.rows=[];state.audit=[];state.summary=null;render();toast("Demo batch restored")}catch(e){toast(e.message)}});
$("tolerance").addEventListener("input",()=> $("diag-tolerance").textContent=$("tolerance").value+" KES");
load().then(run);
