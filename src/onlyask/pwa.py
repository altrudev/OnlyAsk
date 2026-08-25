from __future__ import annotations

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


PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#071217"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"><link rel="manifest" href="/manifest.webmanifest"><link rel="apple-touch-icon" href="/icon-192.png"><title>OnlyAsk</title>
<style>
:root{color-scheme:dark;--bg:#071217;--panel:#0d1d24;--line:#1e3c48;--text:#edf8f9;--muted:#84a5ad;--ok:#72e3a6;--ask:#ffd36f;--deny:#ff808a;--accent:#74d9f0}*{box-sizing:border-box}html,body{margin:0;min-height:100%;background:var(--bg);color:var(--text);font:14px/1.4 Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}body{padding:env(safe-area-inset-top) 0 env(safe-area-inset-bottom)}button,input{font:inherit}.app{max-width:620px;margin:0 auto;min-height:100vh;padding:16px 14px 86px}.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}.brand{display:flex;align-items:center;gap:10px}.logo{width:38px;height:38px;border:1px solid #376c7b;border-radius:12px;display:grid;place-items:center;background:#0b222b;color:var(--accent);font-weight:850}.title{font-size:18px;font-weight:780}.sub{font-size:11px;color:var(--muted)}.pill{border:1px solid var(--line);border-radius:999px;padding:6px 9px;color:var(--ok);font-size:11px}.panel{background:linear-gradient(180deg,#10242c,#0b1a20);border:1px solid var(--line);border-radius:17px;padding:14px;margin-bottom:12px;box-shadow:0 12px 32px rgba(0,0,0,.18)}.mission{font-size:15px;margin-bottom:12px}.command{display:flex;gap:8px}.command input{min-width:0;flex:1;border:1px solid #315463;background:#08171d;color:var(--text);padding:11px 12px;border-radius:11px;outline:none}.btn{border:1px solid #315463;background:#102b35;color:var(--text);padding:10px 12px;border-radius:11px;font-weight:700}.btn:active{transform:translateY(1px)}.btn.primary{background:#123a45;border-color:#458594}.btn.ask{background:#332c17;border-color:#6d5a27;color:#ffe29a}.btn.deny{background:#351a20;border-color:#71333d;color:#ffc1c6}.sectionTitle{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}.sectionTitle strong{font-size:12px;letter-spacing:.06em;text-transform:uppercase}.count{font-size:11px;color:var(--muted)}.decision{border:1px solid #695728;background:#2a2517;border-radius:13px;padding:11px}.decision+.decision{margin-top:8px}.decision strong{display:block;color:var(--ask);margin-bottom:4px}.decision .meta{font-size:11px;color:#c9b97e;overflow-wrap:anywhere}.rowBtns{display:flex;gap:8px;margin-top:10px}.projects{display:grid;gap:8px}.project{border:1px solid #1c3944;border-radius:13px;background:#091920;padding:11px}.projectHead{display:flex;align-items:center;justify-content:space-between;gap:8px}.projectName{font-weight:780}.repo{font:11px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted)}.actions{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:10px}.actions .btn{padding:9px 8px;font-size:12px}.recent{display:grid;gap:7px}.event{border:1px solid #1c3741;border-radius:11px;background:#09181e;padding:9px}.eventHead{display:flex;justify-content:space-between;gap:8px}.state{font-weight:780}.state.verified,.state.recovered{color:var(--ok)}.state.escalated,.state.stale{color:var(--ask)}.state.denied,.state.failed,.state.recovery_failed{color:var(--deny)}pre{white-space:pre-wrap;word-break:break-word;max-height:210px;overflow:auto;background:#061217;border-radius:8px;padding:8px;color:#b8d0d5;font:11px ui-monospace,SFMono-Regular,Menlo,monospace}.nav{position:fixed;bottom:0;left:0;right:0;background:rgba(7,18,23,.94);backdrop-filter:blur(14px);border-top:1px solid var(--line);padding:8px max(12px,env(safe-area-inset-right)) calc(8px + env(safe-area-inset-bottom)) max(12px,env(safe-area-inset-left));display:flex;justify-content:center}.navin{width:min(100%,620px);display:grid;grid-template-columns:repeat(3,1fr);gap:6px}.nav button{border:0;background:transparent;color:var(--muted);padding:8px}.nav button.active{color:var(--accent)}.hide{display:none!important}.login{position:fixed;inset:0;background:#061116;z-index:9;display:grid;place-items:center;padding:24px}.loginCard{width:min(100%,420px);border:1px solid var(--line);border-radius:18px;background:#0d1d24;padding:18px}.loginCard h2{margin:0 0 6px}.loginCard input{width:100%;margin:14px 0 9px;border:1px solid #315463;background:#08171d;color:var(--text);padding:12px;border-radius:11px}.toast{position:fixed;left:50%;bottom:82px;transform:translateX(-50%);max-width:90%;background:#152a33;border:1px solid #315463;padding:9px 12px;border-radius:10px;z-index:10;box-shadow:0 10px 30px rgba(0,0,0,.3)}
</style></head><body>
<div id="login" class="login hide"><div class="loginCard"><div class="brand"><div class="logo">OA</div><div><h2>OnlyAsk</h2><div class="sub">This phone needs a PWA session token. Your GitHub credential stays on the server.</div></div></div><input id="token" type="password" autocomplete="current-password" placeholder="PWA session token"><button class="btn primary" style="width:100%" onclick="saveToken()">Connect</button></div></div>
<div class="app"><header class="top"><div class="brand"><div class="logo">OA</div><div><div class="title">OnlyAsk</div><div class="sub">Dogfood control surface · v0.3</div></div></div><div id="chain" class="pill">● chain</div></header>
<main id="homeView"><section class="panel"><div class="mission" id="objective">Loading authority…</div><div class="command"><input id="command" placeholder="What should I do?"><button class="btn primary" onclick="runCommand()">Run</button></div></section><section class="panel"><div class="sectionTitle"><strong>Needs you</strong><span id="pendingCount" class="count"></span></div><div id="pending"><div class="sub">No human decision needed.</div></div></section><section class="panel"><div class="sectionTitle"><strong>Projects</strong><span class="count">dogfood</span></div><div id="projects" class="projects"></div></section><section class="panel"><div class="sectionTitle"><strong>Recent</strong><span class="count">verified activity</span></div><div id="recent" class="recent"></div></section></main>
<main id="decisionView" class="hide"><section class="panel"><div class="sectionTitle"><strong>Human decisions</strong><span id="decisionCount" class="count"></span></div><div id="decisionList"></div></section></main><main id="ledgerView" class="hide"><section class="panel"><div class="sectionTitle"><strong>Evidence ledger</strong><span id="ledgerCount" class="count"></span></div><div id="ledger"></div></section></main></div>
<nav class="nav"><div class="navin"><button id="nHome" class="active" onclick="view('home')">Home</button><button id="nDecisions" onclick="view('decisions')">Decisions</button><button id="nLedger" onclick="view('ledger')">Ledger</button></div></nav><div id="toast" class="toast hide"></div>
<script>
let STATE=null;const $=id=>document.getElementById(id);const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));function auth(){return localStorage.getItem('onlyask_pwa_token')||''}async function api(path,body){const headers={'content-type':'application/json'};if(auth())headers.authorization='Bearer '+auth();const r=await fetch(path,{method:body?'POST':'GET',headers,body:body?JSON.stringify(body):undefined});let j={};try{j=await r.json()}catch{}if(r.status===401){$('login').classList.remove('hide');throw new Error('Authentication required')}if(!r.ok)throw new Error(j.error||'request failed');return j}function toast(t){$('toast').textContent=t;$('toast').classList.remove('hide');setTimeout(()=>$('toast').classList.add('hide'),2600)}function saveToken(){localStorage.setItem('onlyask_pwa_token',$('token').value);$('login').classList.add('hide');refresh().catch(e=>toast(e.message))}function resultLabel(r){return r?(r.state||r.decision||''):''}function resultText(r){if(!r)return'';if(r.output&&r.output.output)return r.output.output;if(r.output)return JSON.stringify(r.output,null,2);return r.message||''}async function refresh(){STATE=await api('/api/state');$('objective').textContent=STATE.objective;$('chain').textContent=STATE.ledger_valid?'● evidence valid':'● evidence invalid';$('chain').style.color=STATE.ledger_valid?'var(--ok)':'var(--deny)';renderPending();renderProjects();renderRecent();renderLedger()}function renderPending(){const p=STATE.pending||[];$('pendingCount').textContent=p.length?`${p.length} decision${p.length===1?'':'s'}`:'';$('decisionCount').textContent=p.length+'';const html=p.length?p.map(x=>`<div class="decision"><strong>${esc(x.title)}</strong><div class="meta">${esc(JSON.stringify(x.detail))}</div><div class="rowBtns"><button class="btn ask" onclick="approve('${esc(x.transition_id)}')">Approve once</button><button class="btn deny" onclick="rejectDecision('${esc(x.transition_id)}')">Decline</button></div></div>`).join(''):'<div class="sub">No human decision needed.</div>';$('pending').innerHTML=html;$('decisionList').innerHTML=html}function renderProjects(){$('projects').innerHTML=(STATE.projects||[]).map(p=>`<div class="project"><div class="projectHead"><div><div class="projectName">${esc(p.name)}</div><div class="repo">${esc(p.repo)} · ${esc(p.default_branch)}</div></div><span class="pill">configured</span></div><div class="actions"><button class="btn" onclick="act('inspect','${esc(p.repo)}')">Inspect</button><button class="btn" onclick="act('run-tests','${esc(p.repo)}')">Run tests</button><button class="btn ask" style="grid-column:1/-1" onclick="mergePrompt('${esc(p.repo)}')">Request PR merge</button></div></div>`).join('')}function renderRecent(){const rows=STATE.recent||[];$('recent').innerHTML=rows.length?rows.map(r=>`<div class="event"><div class="eventHead"><strong>${esc(r.kind||'event')} · ${esc(r.repo||'')}</strong><span class="state ${esc(resultLabel(r))}">${esc(resultLabel(r))}</span></div><div class="sub">${esc(r.message||'')}</div>${r.output?`<pre>${esc(resultText(r))}</pre>`:''}</div>`).join(''):'<div class="sub">No activity yet.</div>'}function renderLedger(){const rows=STATE.ledger||[];$('ledgerCount').textContent=rows.length+' events';$('ledger').innerHTML=[...rows].reverse().map(e=>`<div class="event"><div class="eventHead"><strong>#${e.sequence} ${esc(e.event)}</strong><span class="sub">${esc(e.transition_id)}</span></div><pre>${esc(JSON.stringify(e.data,null,2))}</pre></div>`).join('')||'<div class="sub">No evidence yet.</div>'}async function act(action,repo){try{const r=await api('/api/action',{action,repo});toast(r.state||'done');await refresh()}catch(e){toast(e.message)}}async function approve(id){try{const r=await api('/api/approve',{transition_id:id});toast(r.state||'approved');await refresh()}catch(e){toast(e.message)}}async function rejectDecision(id){try{await api('/api/reject',{transition_id:id});toast('Declined');await refresh()}catch(e){toast(e.message)}}async function mergePrompt(repo){const n=prompt('Pull request number to merge into main:');if(!n)return;try{const r=await api('/api/action',{action:'request-merge',repo,pr_number:Number(n),method:'squash'});toast(r.state==='escalated'?'Decision queued':r.state);await refresh()}catch(e){toast(e.message)}}async function runCommand(){const text=$('command').value.trim();if(!text)return;const p=(STATE.projects||[])[0];if(!p)return toast('No project configured');const lower=text.toLowerCase();if(lower.includes('test'))return act('run-tests',p.repo);if(lower.includes('inspect')||lower.includes('status'))return act('inspect',p.repo);toast('v0.3 understands “test” and “inspect”; structured commands come next.')}function view(name){for(const id of ['homeView','decisionView','ledgerView'])$(id).classList.add('hide');for(const id of ['nHome','nDecisions','nLedger'])$(id).classList.remove('active');if(name==='home'){$('homeView').classList.remove('hide');$('nHome').classList.add('active')}if(name==='decisions'){$('decisionView').classList.remove('hide');$('nDecisions').classList.add('active')}if(name==='ledger'){$('ledgerView').classList.remove('hide');$('nLedger').classList.add('active')}}if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{});refresh().catch(e=>{if(e.message!=='Authentication required')toast(e.message)});
</script></body></html>'''

MANIFEST = {"name":"OnlyAsk — Governed Operations","short_name":"OnlyAsk","start_url":"/","scope":"/","display":"standalone","background_color":"#071217","theme_color":"#071217","description":"Phone control surface for governed autonomous development operations.","icons":[{"src":"/icon-192.png","sizes":"192x192","type":"image/png","purpose":"any maskable"},{"src":"/icon-512.png","sizes":"512x512","type":"image/png","purpose":"any maskable"}]}
SERVICE_WORKER = r'''const CACHE='onlyask-pwa-v03';const SHELL=['/','/manifest.webmanifest','/icon-192.png','/icon-512.png'];self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL))));self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))));self.addEventListener('fetch',e=>{const u=new URL(e.request.url);if(u.pathname.startsWith('/api/'))return;e.respondWith(fetch(e.request).then(r=>{const copy=r.clone();caches.open(CACHE).then(c=>c.put(e.request,copy));return r}).catch(()=>caches.match(e.request)))})'''


def _png_icon(size: int) -> bytes:
    if size not in {192, 512}:
        raise ValueError("unsupported icon size")
    bg, accent = (7,18,23,255), (116,217,240,255)
    raw=bytearray(); pad=size//6; stroke=max(5,size//32)
    for y in range(size):
        raw.append(0)
        for x in range(size):
            border=((pad<=x<pad+stroke and pad<=y<size-pad) or (size-pad-stroke<=x<size-pad and pad<=y<size-pad) or (pad<=y<pad+stroke and pad<=x<size-pad) or (size-pad-stroke<=y<size-pad and pad<=x<size-pad))
            raw.extend(accent if border else bg)
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',size,size,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(bytes(raw),9))+chunk(b'IEND',b'')


class DogfoodPWA:
    def __init__(self, session: DogfoodSession | None = None, auth_token: str | None = None) -> None:
        self.session=session or DogfoodSession(); self.auth_token=auth_token if auth_token is not None else os.getenv("ONLYASK_PWA_TOKEN",""); self.lock=RLock()
    def authorized(self, header: str | None) -> bool:
        if not self.auth_token:return True
        if not header or not header.startswith("Bearer "):return False
        return hmac.compare_digest(header[7:],self.auth_token)
    def state(self)->dict[str,Any]:
        with self.lock:
            state=self.session.state(); state["runtime"]={"github_token_configured":bool(os.getenv("ONLYASK_GITHUB_TOKEN")),"pwa_auth_required":bool(self.auth_token)}; return state
    def action(self,payload:dict[str,Any])->dict[str,Any]:
        name=str(payload.get("action","")); repo=str(payload.get("repo",""))
        with self.lock:
            if name=="inspect":return self._result(self.session.inspect(repo))
            if name=="run-tests":return self._result(self.session.run_tests(repo))
            if name=="request-merge":return self._result(self.session.request_merge(repo,int(payload.get("pr_number",0)),str(payload.get("method","squash"))))
            raise ValueError("Unknown dogfood action")
    def approve(self,transition_id:str)->dict[str,Any]:
        with self.lock:
            if transition_id not in self.session.pending:raise KeyError("Pending decision not found")
            return self._result(self.session.approve_once(transition_id))
    def reject(self,transition_id:str)->dict[str,Any]:
        with self.lock:
            if transition_id not in self.session.pending:raise KeyError("Pending decision not found")
            return self.session.reject(transition_id)
    @staticmethod
    def _result(result:Any)->dict[str,Any]:
        return {"transition_id":result.transition_id,"state":result.state.value,"decision":result.decision.kind.value,"message":result.message,"verification_passed":result.verification_passed,"recovery_passed":result.recovery_passed,"output":result.output}


def make_handler(app:DogfoodPWA)->type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version="OnlyAsk-PWA/0.3"
        def log_message(self,format:str,*args:Any)->None:return
        def _headers(self)->None:
            self.send_header("Cache-Control","no-store");self.send_header("X-Content-Type-Options","nosniff");self.send_header("X-Frame-Options","DENY");self.send_header("Referrer-Policy","no-referrer");self.send_header("Content-Security-Policy","default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        def _send(self,status:HTTPStatus,body:bytes,content_type:str,cache:str="no-store")->None:
            self.send_response(status.value);self.send_header("Content-Type",content_type);self.send_header("Content-Length",str(len(body)));self._headers();
            if cache!="no-store":self.send_header("Cache-Control",cache)
            self.end_headers();self.wfile.write(body)
        def _json(self,status:HTTPStatus,payload:dict[str,Any])->None:self._send(status,json.dumps(payload,default=str).encode(),"application/json; charset=utf-8")
        def _read_json(self)->dict[str,Any]:
            try:length=int(self.headers.get("Content-Length","0"))
            except ValueError as exc:raise ValueError("Invalid Content-Length") from exc
            if length<0 or length>32768:raise ValueError("Request body too large")
            raw=self.rfile.read(length) if length else b"{}";value=json.loads(raw.decode("utf-8"))
            if not isinstance(value,dict):raise ValueError("JSON object required")
            return value
        def _auth(self)->bool:
            if app.authorized(self.headers.get("Authorization")):return True
            self._json(HTTPStatus.UNAUTHORIZED,{"error":"Authentication required"});return False
        def do_GET(self)->None:
            path=urlparse(self.path).path
            if path=="/":self._send(HTTPStatus.OK,PAGE.encode(),"text/html; charset=utf-8");return
            if path=="/manifest.webmanifest":self._send(HTTPStatus.OK,json.dumps(MANIFEST).encode(),"application/manifest+json","public,max-age=3600");return
            if path=="/sw.js":self._send(HTTPStatus.OK,SERVICE_WORKER.encode(),"application/javascript; charset=utf-8","no-cache");return
            if path in {"/icon-192.png","/icon-512.png"}:self._send(HTTPStatus.OK,_png_icon(192 if "192" in path else 512),"image/png","public,max-age=86400");return
            if path=="/api/state":
                if self._auth():self._json(HTTPStatus.OK,app.state())
                return
            self._json(HTTPStatus.NOT_FOUND,{"error":"Not found"})
        def do_POST(self)->None:
            if not self._auth():return
            path=urlparse(self.path).path
            try:
                payload=self._read_json()
                if path=="/api/action":self._json(HTTPStatus.OK,app.action(payload));return
                if path=="/api/approve":self._json(HTTPStatus.OK,app.approve(str(payload.get("transition_id",""))));return
                if path=="/api/reject":self._json(HTTPStatus.OK,app.reject(str(payload.get("transition_id",""))));return
                self._json(HTTPStatus.NOT_FOUND,{"error":"Not found"})
            except (ValueError,TypeError,json.JSONDecodeError) as exc:self._json(HTTPStatus.BAD_REQUEST,{"error":str(exc)})
            except KeyError as exc:self._json(HTTPStatus.NOT_FOUND,{"error":str(exc)})
            except Exception as exc:self._json(HTTPStatus.BAD_GATEWAY,{"error":f"Backend action failed: {type(exc).__name__}"})
    return Handler


def serve(host:str="127.0.0.1",port:int=8787)->None:
    if not 1<=port<=65535:raise ValueError("port must be between 1 and 65535")
    token=os.getenv("ONLYASK_PWA_TOKEN","")
    if host not in {"127.0.0.1","localhost","::1"} and not token:raise RuntimeError("ONLYASK_PWA_TOKEN is required when binding beyond loopback")
    app=DogfoodPWA(auth_token=token);server=ThreadingHTTPServer((host,port),make_handler(app));print(f"OnlyAsk Dogfood PWA: http://{host}:{port}");print("Installable PWA requires HTTPS when accessed from another device.")
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
