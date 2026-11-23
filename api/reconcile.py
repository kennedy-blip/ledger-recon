"""Reference and amount reconciliation plus exception workflow."""
from http.server import BaseHTTPRequestHandler
import json, math
from datetime import datetime, timezone
from api._db import db, LOCK
def send(h,code,data):
 b=json.dumps(data,allow_nan=False).encode(); h.send_response(code); h.send_header("Content-Type","application/json; charset=utf-8"); h.send_header("Cache-Control","no-store"); h.send_header("Content-Length",str(len(b))); h.end_headers(); h.wfile.write(b)
def add(c,ref,kind,ia,ga,diff,currency,now):
 cur=c.execute("INSERT INTO reconciliation_exceptions(reference_id,exception_type,internal_amount,gateway_amount,diff,currency,status,created_at) VALUES(?,?,?,?,?,?,'OPEN',?)",(ref,kind,ia,ga,diff,currency,now))
 return {"referenceId":ref,"type":kind,"internalAmount":ia,"gatewayAmount":ga,"diff":diff,"currency":currency,"status":"OPEN","exceptionId":cur.lastrowid,"resolutionNote":""}
def run(c,tol):
 c.execute("DELETE FROM reconciliation_exceptions WHERE status IN ('OPEN','INVESTIGATING')")
 ins=c.execute("SELECT * FROM internal_ledger ORDER BY id").fetchall(); outs=c.execute("SELECT * FROM gateway_settlements ORDER BY id").fetchall()
 groups={}; counts={}
 for g in outs: groups.setdefault(g["reference_id"],[]).append(g)
 for i in ins: counts[i["reference_id"]]=counts.get(i["reference_id"],0)+1
 seen=set(); rows=[]; matched_value=0.0; delta=0.0; now=datetime.now(timezone.utc).isoformat()
 for i in ins:
  ref=i["reference_id"]; gs=groups.get(ref,[])
  if counts[ref]>1 or len(gs)>1:
   rows.append(add(c,ref,"DUPLICATE_REF",i["amount"],sum(g["amount"] for g in gs) if gs else None,0,i["currency"],now)); seen.update(g["id"] for g in gs); continue
  if not gs:
   rows.append(add(c,ref,"MISSING_IN_GATEWAY",i["amount"],None,-i["amount"],i["currency"],now)); delta-=i["amount"]; continue
  g=gs[0]; seen.add(g["id"]); diff=round(g["amount"]-i["amount"],4)
  if i["currency"]==g["currency"] and abs(diff)<=tol:
   rows.append({"referenceId":ref,"type":"MATCHED","internalAmount":i["amount"],"gatewayAmount":g["amount"],"diff":diff,"currency":i["currency"],"status":"MATCHED","exceptionId":None}); matched_value+=min(i["amount"],g["amount"])
  else:
   rows.append(add(c,ref,"AMOUNT_MISMATCH",i["amount"],g["amount"],diff,i["currency"],now)); delta+=diff
 for g in outs:
  if g["id"] not in seen and g["reference_id"] not in counts:
   rows.append(add(c,g["reference_id"],"UNMATCHED_GATEWAY",None,g["amount"],g["amount"],g["currency"],now)); delta+=g["amount"]
 c.commit(); types={}
 for r in rows: types[r["type"]]=types.get(r["type"],0)+1
 exceptions=[r for r in rows if r["type"]!="MATCHED"]
 audit=[dict(exceptionId=r["id"],referenceId=r["reference_id"],type=r["exception_type"],status=r["status"],resolutionNote=r["resolution_note"]) for r in c.execute("SELECT * FROM reconciliation_exceptions ORDER BY id DESC")]
 return {"ok":True,"totals":{"total":len(rows),"matched":types.get("MATCHED",0),"exceptions":len(exceptions),"matchedValue":round(matched_value,2),"unmatchedDeltaValue":round(delta,2),"byType":types},"rows":rows,"exceptions":exceptions,"audit":audit}
class handler(BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def do_POST(self):
  if self.path.split("?")[0]!="/api/reconcile": return send(self,404,{"error":"Not found"})
  try:
   n=int(self.headers.get("Content-Length","0"))
   if n>100000: return send(self,413,{"error":"Payload too large"})
   data=json.loads(self.rfile.read(n) or b"{}")
   with LOCK:
    c=db(); action=data.get("action","run")
    if action in ("resolve","investigate"):
     eid=int(data.get("exceptionId",0)); status="RESOLVED" if action=="resolve" else "INVESTIGATING"
     cur=c.execute("UPDATE reconciliation_exceptions SET status=?,resolution_note=? WHERE id=?",(status,str(data.get("resolutionNote",""))[:1000],eid)); c.commit()
     if not cur.rowcount: return send(self,404,{"error":"Exception not found"})
     return send(self,200,{"ok":True,"exceptionId":eid,"status":status})
    tol=float(data.get("amountTolerance",0.01))
    if not math.isfinite(tol) or tol<0 or tol>1000000: return send(self,400,{"error":"Invalid amountTolerance"})
    return send(self,200,run(c,tol))
  except (ValueError,TypeError,json.JSONDecodeError) as e: return send(self,400,{"error":str(e)})
  except Exception as e: return send(self,500,{"error":str(e)})
