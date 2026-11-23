"""Batch import and demo reset endpoint."""
from http.server import BaseHTTPRequestHandler
import json
from api._db import db, replace, reset, editor_rows
def send(h,code,data):
 b=json.dumps(data,allow_nan=False).encode(); h.send_response(code); h.send_header("Content-Type","application/json; charset=utf-8"); h.send_header("Cache-Control","no-store"); h.send_header("Content-Length",str(len(b))); h.end_headers(); h.wfile.write(b)
class handler(BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def do_GET(self):
  if self.path.split("?")[0]!="/api/batches": return send(self,404,{"error":"Not found"})
  try:
   ins,outs=editor_rows(); db()
   return send(self,200,{"engine":"sqlite","status":"active","summary":{"internalRows":len(ins),"gatewayRows":len(outs)},"internalRows":ins,"gatewayRows":outs})
  except Exception as e: return send(self,500,{"error":str(e)})
 def do_POST(self):
  if self.path.split("?")[0]!="/api/batches": return send(self,404,{"error":"Not found"})
  try:
   n=int(self.headers.get("Content-Length","0"))
   if n>2000000: return send(self,413,{"error":"Payload too large"})
   data=json.loads(self.rfile.read(n) or b"{}")
   if data.get("reset"): reset()
   else: replace(data.get("internalRows",[]),data.get("gatewayRows",[]))
   ins,outs=editor_rows(); return send(self,200,{"ok":True,"internalRows":ins,"gatewayRows":outs})
  except (ValueError,json.JSONDecodeError) as e: return send(self,400,{"error":str(e)})
  except Exception as e: return send(self,500,{"error":str(e)})
