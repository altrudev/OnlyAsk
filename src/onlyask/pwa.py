from __future__ import annotations

import hashlib
import hmac
import json
import os
import struct
import zlib
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import RLock
from typing import Any
from urllib.parse import urlparse

from .dogfood import DogfoodSession

PAGE = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#071217"><meta name="apple-mobile-web-app-capable" content="yes"><link rel="manifest" href="/manifest.webmanifest"><link rel="apple-touch-icon" href="/icon-192.png"><title>OnlyAsk</title><style>
:root{color-scheme:dark;--b:#071217;--p:#0d1d24;--l:#1e3c48;--t:#edf8f9;--m:#84a5ad;--o:#72e3a6;--a:#ffd36f;--d:#ff808a;--x:#74d9f0}*{box-sizing:border-box}body{margin:0;background:var(--b);color:var(--t);font:14px system-ui;padding:env(safe-area-inset-top) 0 env(safe-area-inset-bottom)}.app{max-width:620px;margin:auto;padding:14px 13px 78px}.top,.head,.r{display:flex;align-items:center;justify-content:space-between;gap:8px}.brand{display:flex;align-items:center;gap:9px}.logo{width:38px;height:38px;border:1px solid #376c7b;border-radius:12px;display:grid;place-items:center;color:var(--x);font-weight:900}.muted{color:var(--m);font-size:11px}.panel{background:var(--p);border:1px solid var(--l);border-radius:16px;padding:13px;margin:11px 0}.panel h3{font-size:12px;text-transform:uppercase;letter-spacing:.07em;margin:0 0 10px}.mission{font-size:15px;margin-bottom:10px}.cmd{display:flex;gap:7px}.cmd input{flex:1;min-width:0}.btn,input{border:1px solid #315463;background:#102b35;color:var(--t);border-radius:10px;padding:10px;font:inherit}.btn{font-weight:700}.ask{border-color:#6d5a27;background:#332c17;color:#ffe29a}.deny{border-color:#71333d;background:#351a20;color:#ffc1c6}.card{border:1px solid #1c3944;background:#091920;border-radius:12px;padding:10px;margin-top:8px}.repo{font:11px ui-monospace;color:var(--m)}.actions{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:9px}.actions .wide{grid-column:1/-1}.state{font-weight:800}.verified,.recovered{color:var(--o)}.escalated,.stale{color:var(--a)}.denied,.failed,.recovery_failed,.uncertain{color:var(--d)}pre{white-space:pre-wrap;word-break:break-word;max-height:190px;overflow:auto;background:#061217;border-radius:8px;padding:8px;font:11px ui-monospace;color:#b8d0d5}.nav{position:fixed;bottom:0;left:0;right:0;background:#071217ee;border-top:1px solid var(--l);padding:7px 12px calc(7px + env(safe-area-inset-bottom));display:flex;justify-content:center}.nav div{width:min(620px,100%);display:grid;grid-template-columns:repeat(3,1fr)}.nav button{border:0;background:none;color:var(--m);padding:8px}.nav .on{color:var(--x)}.hide{display:none!important}.login{position:fixed;inset:0;z-index:9;background:#061116;display:grid;place-items:center;padding:22px}.login>div{width:min(420px,100%)}.toast{position:fixed;z-index:10;left:50%;bottom:76px;transform:translateX(-50%);background:#152a33;border:1px solid #315463;padding:9px 12px;border-radius:10px;max-width:90%}
</style></head><body><div id="login" class="login hide"><div class="panel"><div class="brand"><div class="logo">OA</div><div><b>OnlyAsk</b><div class="muted">Enter the PWA session token. GitHub credentials never reach this phone.</div></div></div><input id="tok" type="password" placeholder="PWA session token" style="width:100%;margin:12px 0 8px"><button class="btn" style="width:100%" onclick="login()">Connect</button></div></div><div class="app"><header class="top"><div class="brand"><div class="logo">OA</div><div><b>OnlyAsk</b><div class="muted">Dogfood PWA · v0.3</div></div></div><span id="chain" class="state verified">● evidence</span></header><main id="home"><section class="panel"><div id="objective" class="mission">Loading authority…</div><div class="cmd"><input id="cmd" placeholder="test OnlyAsk / inspect OnlyAsk"><button class="btn" onclick="command()">Run</button></div></section><section class="panel"><div class="head"><h3>Needs you</h3><span id="pc" class="muted"></span></div><div id="pending" class="muted">No decision needed.</div></section><section class="panel"><h3>Projects</h3><div id="projects"></div></section><section class="panel"><h3>Recent</h3><div id="recent" class="muted">No activity yet.</div></section></main><main id="decisions" class="hide"><section class="panel"><h3>Human decisions</h3><div id="decisionList"></div></section></main><main id="ledgerView" class="hide"><section class="panel"><h3>Evidence ledger</h3><div id="ledger"></div></section></main></div><nav class="nav"><div><button id="nh" class="on" onclick="view('home')">Home</button><button id="nd" onclick="view('decisions')">Decisions</button><button id="nl" onclick="view('ledger')">Ledger</button></div></nav><div id="toast" class="toast hide"></div><script>
let S=null;const $=x=>document.getElementById(x),esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));async function api(p,b){const r=await fetch(p,{method:b?'POST':'GET',headers:{'content-type':'application/json'},credentials:'same-origin',body:b?JSON.stringify(b):undefined});let j={};try{j=await r.json()}catch{}if(r.status===401){$('login').classList.remove('hide');throw Error('Authentication required')}if(!r.ok)throw Error(j.error||'request failed');return j}function toast(t){$('toast').textContent=t;$('toast').classList.remove('hide');setTimeout(()=>$('toast').classList.add('hide'),2200)}async function login(){try{await api('/api/login',{token:$('tok').value});$('tok').value='';$('login').classList.add('hide');await refresh()}catch(e){toast(e.message)}}function result(r){return r?.state||r?.decision||''}function out(r){if(r?.output?.output)return r.output.output;if(r?.output)return JSON.stringify(r.output,null,2);return r?.message||''}async function refresh(){S=await api('/api/state');$('objective').textContent=S.objective;$('chain').textContent=S.ledger_valid?'● evidence valid':'● evidence invalid';$('chain').className='state '+(S.ledger_valid?'verified':'denied');render()}function render(){const p=S.pending||[];$('pc').textContent=p.length?`${p.length} decision${p.length===1?'':'s'}`:'';const ph=p.length?p.map(x=>`<div class="card"><b class="state escalated">${esc(x.title)}</b><div class="repo">${esc(JSON.stringify(x.detail))}</div><div class="r" style="margin-top:8px"><button class="btn ask" onclick="approve('${esc(x.transition_id)}')">Approve once</button><button class="btn deny" onclick="rejectD('${esc(x.transition_id)}')">Decline</button></div></div>`).join(''):'<div class="muted">No human decision needed.</div>';$('pending').innerHTML=ph;$('decisionList').innerHTML=ph;$('projects').innerHTML=(S.projects||[]).map(x=>`<div class="card"><div class="r"><b>${esc(x.name)}</b><span class="repo">${esc(x.default_branch)}</span></div><div class="repo">${esc(x.repo)}</div><div class="actions"><button class="btn" onclick="act('inspect','${esc(x.repo)}')">Inspect</button><button class="btn" onclick="act('run-tests','${esc(x.repo)}')">Run tests</button><button class="btn ask wide" onclick="merge('${esc(x.repo)}')">Request PR merge</button></div></div>`).join('');const rr=S.recent||[];$('recent').innerHTML=rr.length?rr.map(x=>`<div class="card"><div class="r"><b>${esc(x.kind||'event')} · ${esc(x.repo||'')}</b><span class="state ${esc(result(x))}">${esc(result(x))}</span></div><div class="muted">${esc(x.message||'')}</div>${x.output?`<pre>${esc(out(x))}</pre>`:''}</div>`).join(''):'<div class="muted">No activity yet.</div>';$('ledger').innerHTML=[...(S.ledger||[])].reverse().map(e=>`<div class="card"><div class="r"><b>#${e.sequence} ${esc(e.event)}</b><span class="repo">${esc(e.transition_id)}</span></div><pre>${esc(JSON.stringify(e.data,null,2))}</pre></div>`).join('')||'<div class="muted">No evidence yet.</div>'}async function act(a,r){try{const x=await api('/api/action',{action:a,repo:r});toast(x.state);await refresh()}catch(e){toast(e.message)}}async function approve(id){try{const x=await api('/api/approve',{transition_id:id});toast(x.state);await refresh()}catch(e){toast(e.message)}}async function rejectD(id){try{await api('/api/reject',{transition_id:id});toast('Declined');await refresh()}catch(e){toast(e.message)}}async function merge(r){const n=prompt('PR number to merge into main:');if(!n)return;try{const x=await api('/api/action',{action:'request-merge',repo:r,pr_number:Number(n),method:'squash'});toast(x.state==='escalated'?'Decision queued':x.state);await refresh()}catch(e){toast(e.message)}}function command(){const t=$('cmd').value.toLowerCase(),p=(S.projects||[])[0];if(!p)return;if(t.includes('test'))return act('run-tests',p.repo);if(t.includes('inspect')||t.includes('status'))return act('inspect',p.repo);toast('v0.3 understands test and inspect')}function view(v){for(const x of ['home','decisions','ledgerView'])$(x).classList.add('hide');for(const x of ['nh','nd','nl'])$(x).classList.remove('on');if(v==='home'){$('home').classList.remove('hide');$('nh').classList.add('on')}if(v==='decisions'){$('decisions').classList.remove('hide');$('nd').classList.add('on')}if(v==='ledger'){$('ledgerView').classList.remove('hide');$('nl').classList.add('on')}}if('serviceWorker'in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{});refresh().catch(e=>{if(e.message!=='Authentication required')toast(e.message)});
</script></body></html>'''

MANIFEST={"name":"OnlyAsk — Governed Operations","short_name":"OnlyAsk","start_url":"/","scope":"/","display":"standalone","background_color":"#071217","theme_color":"#071217","icons":[{"src":"/icon-192.png","sizes":"192x192","type":"image/png","purpose":"any maskable"},{"src":"/icon-512.png","sizes":"512x512","type":"image/png","purpose":"any maskable"}]}
SERVICE_WORKER="""const CACHE='onlyask-v03';const SHELL=['/','/manifest.webmanifest','/icon-192.png','/icon-512.png'];self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL))));self.addEventListener('fetch',e=>{const u=new URL(e.request.url);if(u.pathname.startsWith('/api/'))return;e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)))})"""


def _png_icon(size:int)->bytes:
    if size not in {192,512}:raise ValueError("unsupported icon size")
    raw=bytearray();pad=size//6;stroke=max(5,size//32);bg=(7,18,23,255);accent=(116,217,240,255)
    for y in range(size):
        raw.append(0)
        for x in range(size):
            border=(pad<=x<pad+stroke or size-pad-stroke<=x<size-pad) and pad<=y<size-pad or (pad<=y<pad+stroke or size-pad-stroke<=y<size-pad) and pad<=x<size-pad
            raw.extend(accent if border else bg)
    def chunk(k:bytes,d:bytes)->bytes:return struct.pack('>I',len(d))+k+d+struct.pack('>I',zlib.crc32(k+d)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',size,size,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(bytes(raw),9))+chunk(b'IEND',b'')


class DogfoodPWA:
    def __init__(self,session:DogfoodSession|None=None,auth_token:str|None=None)->None:
        self.session=session or DogfoodSession();self.auth_token=auth_token if auth_token is not None else os.getenv("ONLYASK_PWA_TOKEN","");self.lock=RLock()
    @property
    def session_cookie(self)->str:
        return hashlib.sha256(("OnlyAsk/v0.3/session/"+self.auth_token).encode()).hexdigest() if self.auth_token else ""
    def login(self,supplied:str)->bool:return bool(self.auth_token) and hmac.compare_digest(supplied,self.auth_token)
    def authorized(self,header:str|None,cookie_header:str|None=None)->bool:
        if not self.auth_token:return True
        if header and header.startswith("Bearer ") and hmac.compare_digest(header[7:],self.auth_token):return True
        cookies={}
        for part in (cookie_header or "").split(";"):
            if "=" in part:
                k,v=part.strip().split("=",1);cookies[k]=v
        return hmac.compare_digest(cookies.get("oa_session",""),self.session_cookie)
    def state(self)->dict[str,Any]:
        with self.lock:
            s=self.session.state();s["runtime"]={"github_token_configured":bool(os.getenv("ONLYASK_GITHUB_TOKEN")),"pwa_auth_required":bool(self.auth_token)};return s
    def action(self,p:dict[str,Any])->dict[str,Any]:
        with self.lock:
            a,r=str(p.get("action","")),str(p.get("repo",""))
            if a=="inspect":return self._result(self.session.inspect(r))
            if a=="run-tests":return self._result(self.session.run_tests(r))
            if a=="request-merge":return self._result(self.session.request_merge(r,int(p.get("pr_number",0)),str(p.get("method","squash"))))
            raise ValueError("Unknown dogfood action")
    def approve(self,t:str)->dict[str,Any]:
        with self.lock:
            if t not in self.session.pending:raise KeyError("Pending decision not found")
            return self._result(self.session.approve_once(t))
    def reject(self,t:str)->dict[str,Any]:
        with self.lock:
            if t not in self.session.pending:raise KeyError("Pending decision not found")
            return self.session.reject(t)
    @staticmethod
    def _result(r:Any)->dict[str,Any]:return {"transition_id":r.transition_id,"state":r.state.value,"decision":r.decision.kind.value,"message":r.message,"verification_passed":r.verification_passed,"recovery_passed":r.recovery_passed,"output":r.output}


def make_handler(app:DogfoodPWA)->type[BaseHTTPRequestHandler]:
    class H(BaseHTTPRequestHandler):
        server_version="OnlyAsk-PWA/0.3"
        def log_message(self,format:str,*args:Any)->None:return
        def headers_(self)->None:
            self.send_header("Cache-Control","no-store");self.send_header("X-Content-Type-Options","nosniff");self.send_header("X-Frame-Options","DENY");self.send_header("Referrer-Policy","no-referrer");self.send_header("Content-Security-Policy","default-src 'self';style-src 'unsafe-inline';script-src 'unsafe-inline';connect-src 'self';img-src 'self';frame-ancestors 'none';base-uri 'none'")
        def send_(self,status:HTTPStatus,body:bytes,typ:str,cache:str="no-store")->None:
            self.send_response(status.value);self.send_header("Content-Type",typ);self.send_header("Content-Length",str(len(body)));self.headers_();
            if cache!="no-store":self.send_header("Cache-Control",cache)
            self.end_headers();self.wfile.write(body)
        def json_(self,status:HTTPStatus,p:dict[str,Any])->None:self.send_(status,json.dumps(p,default=str).encode(),"application/json; charset=utf-8")
        def read_(self)->dict[str,Any]:
            try:n=int(self.headers.get("Content-Length","0"))
            except ValueError as e:raise ValueError("Invalid Content-Length") from e
            if n<0 or n>32768:raise ValueError("Request body too large")
            v=json.loads((self.rfile.read(n) if n else b"{}").decode())
            if not isinstance(v,dict):raise ValueError("JSON object required")
            return v
        def auth_(self)->bool:
            if app.authorized(self.headers.get("Authorization"),self.headers.get("Cookie")):return True
            self.json_(HTTPStatus.UNAUTHORIZED,{"error":"Authentication required"});return False
        def do_GET(self)->None:
            p=urlparse(self.path).path
            if p=="/":return self.send_(HTTPStatus.OK,PAGE.encode(),"text/html; charset=utf-8")
            if p=="/manifest.webmanifest":return self.send_(HTTPStatus.OK,json.dumps(MANIFEST).encode(),"application/manifest+json","public,max-age=3600")
            if p=="/sw.js":return self.send_(HTTPStatus.OK,SERVICE_WORKER.encode(),"application/javascript","no-cache")
            if p in {"/icon-192.png","/icon-512.png"}:return self.send_(HTTPStatus.OK,_png_icon(192 if "192" in p else 512),"image/png","public,max-age=86400")
            if p=="/api/state":
                if self.auth_():self.json_(HTTPStatus.OK,app.state())
                return
            self.json_(HTTPStatus.NOT_FOUND,{"error":"Not found"})
        def do_POST(self)->None:
            p=urlparse(self.path).path
            try:
                body=self.read_()
                if p=="/api/login":
                    if not app.login(str(body.get("token",""))):return self.json_(HTTPStatus.UNAUTHORIZED,{"error":"Invalid session token"})
                    raw=b'{"ok":true}';self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(raw)));self.headers_();cookie=f"oa_session={app.session_cookie}; Path=/; HttpOnly; SameSite=Strict; Max-Age=2592000";cookie+=("; Secure" if os.getenv("ONLYASK_SECURE_COOKIE","1")!="0" else "");self.send_header("Set-Cookie",cookie);self.end_headers();self.wfile.write(raw);return
                if not self.auth_():return
                if p=="/api/action":return self.json_(HTTPStatus.OK,app.action(body))
                if p=="/api/approve":return self.json_(HTTPStatus.OK,app.approve(str(body.get("transition_id",""))))
                if p=="/api/reject":return self.json_(HTTPStatus.OK,app.reject(str(body.get("transition_id",""))))
                self.json_(HTTPStatus.NOT_FOUND,{"error":"Not found"})
            except (ValueError,TypeError,json.JSONDecodeError) as e:self.json_(HTTPStatus.BAD_REQUEST,{"error":str(e)})
            except KeyError as e:self.json_(HTTPStatus.NOT_FOUND,{"error":str(e)})
            except Exception as e:self.json_(HTTPStatus.BAD_GATEWAY,{"error":f"Backend action failed: {type(e).__name__}"})
    return H


def serve(host:str="127.0.0.1",port:int=8787)->None:
    if not 1<=port<=65535:raise ValueError("port must be between 1 and 65535")
    token=os.getenv("ONLYASK_PWA_TOKEN","")
    if host not in {"127.0.0.1","localhost","::1"} and not token:raise RuntimeError("ONLYASK_PWA_TOKEN is required when binding beyond loopback")
    server=ThreadingHTTPServer((host,port),make_handler(DogfoodPWA(auth_token=token)));print(f"OnlyAsk Dogfood PWA: http://{host}:{port}");print("Remote phone installation requires HTTPS.")
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
