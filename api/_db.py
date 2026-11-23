"""Shared in-process SQLite database and demo seed."""
import json, sqlite3, threading, math
from datetime import datetime, timezone
LOCK = threading.RLock()
DB = None
INTERNAL = [
 {"referenceId":"TXN-90412","amount":1450,"currency":"KES","timestamp":"2026-11-22T08:12:00Z","status":"POSTED"},
 {"referenceId":"TXN-90413","amount":820,"currency":"KES","timestamp":"2026-11-22T08:15:00Z","status":"POSTED"},
 {"referenceId":"TXN-90414","amount":2500,"currency":"KES","timestamp":"2026-11-22T08:20:00Z","status":"POSTED"},
 {"referenceId":"TXN-90415","amount":640,"currency":"KES","timestamp":"2026-11-22T08:25:00Z","status":"POSTED"},
 {"referenceId":"TXN-90416","amount":1199,"currency":"KES","timestamp":"2026-11-22T08:31:00Z","status":"POSTED"},
 {"referenceId":"TXN-90417","amount":375.5,"currency":"KES","timestamp":"2026-11-22T08:38:00Z","status":"POSTED"},
 {"referenceId":"TXN-90418","amount":910,"currency":"KES","timestamp":"2026-11-22T08:44:00Z","status":"POSTED"},
 {"referenceId":"TXN-90419","amount":500,"currency":"KES","timestamp":"2026-11-22T08:51:00Z","status":"POSTED"}]
GATEWAY = [
 {"referenceId":"TXN-90412","amount":1450,"currency":"KES","timestamp":"2026-11-22T08:13:00Z","status":"SETTLED"},
 {"referenceId":"TXN-90413","amount":819.5,"currency":"KES","timestamp":"2026-11-22T08:16:00Z","status":"SETTLED"},
 {"referenceId":"TXN-90414","amount":2490,"currency":"KES","timestamp":"2026-11-22T08:21:00Z","status":"SETTLED"},
 {"referenceId":"TXN-90415","amount":640,"currency":"KES","timestamp":"2026-11-22T08:26:00Z","status":"SETTLED"},
 {"referenceId":"TXN-90415","amount":640,"currency":"KES","timestamp":"2026-11-22T08:27:00Z","status":"SETTLED"},
 {"referenceId":"TXN-90417","amount":375.5,"currency":"KES","timestamp":"2026-11-22T08:39:00Z","status":"SETTLED"},
 {"referenceId":"GW-UNMAPPED-77","amount":1220,"currency":"KES","timestamp":"2026-11-22T08:45:00Z","status":"SETTLED"}]
def clean(x):
 if not isinstance(x,dict): raise ValueError("Rows must be JSON objects.")
 ref=str(x.get("referenceId","")).strip(); cur=str(x.get("currency","KES")).strip().upper()
 try: amount=float(x["amount"])
 except (KeyError,TypeError,ValueError): raise ValueError("Each row needs a numeric amount.")
 if not ref or len(ref)>120 or not cur or len(cur)>8 or not math.isfinite(amount) or amount<0: raise ValueError("Invalid reference, currency, or amount.")
 return {"referenceId":ref,"amount":round(amount,4),"currency":cur,"timestamp":str(x.get("timestamp",""))[:80],"status":str(x.get("status","POSTED"))[:32]}
def connect():
 c=sqlite3.connect(":memory:",check_same_thread=False); c.row_factory=sqlite3.Row
 c.executescript("""
 CREATE TABLE internal_ledger(id INTEGER PRIMARY KEY,reference_id TEXT NOT NULL,amount REAL NOT NULL,currency TEXT NOT NULL,timestamp TEXT,status TEXT,raw_json TEXT NOT NULL);
 CREATE TABLE gateway_settlements(id INTEGER PRIMARY KEY,reference_id TEXT NOT NULL,amount REAL NOT NULL,currency TEXT NOT NULL,timestamp TEXT,status TEXT,raw_json TEXT NOT NULL);
 CREATE TABLE reconciliation_exceptions(id INTEGER PRIMARY KEY,reference_id TEXT NOT NULL,exception_type TEXT NOT NULL,internal_amount REAL,gateway_amount REAL,diff REAL NOT NULL,currency TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'OPEN',resolution_note TEXT DEFAULT '',created_at TEXT NOT NULL);
 """); return c
def db():
 global DB
 with LOCK:
  if DB is None:
   DB=connect(); seed(DB,INTERNAL,GATEWAY)
  return DB
def seed(c, ins, outs):
 c.execute("DELETE FROM internal_ledger"); c.execute("DELETE FROM gateway_settlements"); c.execute("DELETE FROM reconciliation_exceptions")
 for table,items in (("internal_ledger",ins),("gateway_settlements",outs)):
  for raw in items:
   x=clean(raw); c.execute("INSERT INTO "+table+"(reference_id,amount,currency,timestamp,status,raw_json) VALUES(?,?,?,?,?,?)",(x["referenceId"],x["amount"],x["currency"],x["timestamp"],x["status"],json.dumps(x)))
 c.commit()
def replace(ins,outs):
 if not isinstance(ins,list) or not isinstance(outs,list) or len(ins)>5000 or len(outs)>5000: raise ValueError("Provide arrays of at most 5,000 rows per side.")
 with LOCK: seed(db(),ins,outs)
def reset():
 with LOCK: seed(db(),INTERNAL,GATEWAY)
def editor_rows():
 c=db()
 return ([json.loads(r[0]) for r in c.execute("SELECT raw_json FROM internal_ledger ORDER BY id")],
         [json.loads(r[0]) for r in c.execute("SELECT raw_json FROM gateway_settlements ORDER BY id")])
