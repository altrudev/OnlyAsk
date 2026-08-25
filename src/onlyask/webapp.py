from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import RLock
from typing import Any
from urllib.parse import urlparse

from .product import OnlyAskProductSession


PAGE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OnlyAsk — Governed Autonomous Operations</title>
<style>
:root{color-scheme:dark;--bg:#071015;--panel:#0d1b22;--panel2:#112630;--line:#21404c;--text:#eaf6f7;--muted:#8aa7ae;--ok:#72e3a6;--ask:#ffd36f;--deny:#ff808a;--accent:#6ed7f2}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 15% 0%,#12313d 0,#071015 42%);color:var(--text);font:14px/1.45 Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}.shell{max-width:1440px;margin:auto;padding:22px}.top{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:18px}.brand{display:flex;align-items:center;gap:12px}.mark{width:38px;height:38px;border:1px solid #3b7180;border-radius:12px;display:grid;place-items:center;background:#0b2029;font-weight:800;color:var(--accent)}h1{font-size:20px;margin:0}.sub{color:var(--muted);font-size:12px}.badge{border:1px solid var(--line);border-radius:999px;padding:7px 11px;color:var(--muted);background:#09161c}.grid{display:grid;grid-template-columns:1.2fr .8fr;gap:14px}.panel{background:linear-gradient(180deg,rgba(17,38,48,.95),rgba(10,25,32,.95));border:1px solid var(--line);border-radius:16px;overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,.22)}.hd{display:flex;align-items:center;justify-content:space-between;padding:13px 15px;border-bottom:1px solid var(--line)}.hd strong{font-size:13px}.body{padding:15px}.objective{font-size:17px;max-width:820px;margin:0 0 14px}.actions{display:flex;flex-wrap:wrap;gap:8px}.btn{appearance:none;border:1px solid #315866;background:#102b35;color:var(--text);border-radius:10px;padding:9px 12px;font-weight:650;cursor:pointer}.btn:hover{border-color:#61a9ba}.btn.primary{background:#123b46;border-color:#3c8495}.btn.warn{background:#342c17;border-color:#6e5b27}.btn.danger{background:#351a20;border-color:#71333d}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:14px}.stat{border:1px solid var(--line);border-radius:12px;padding:10px;background:#0a1a21}.stat b{display:block;font-size:21px}.stat span{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.08em}.two{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px}.rules{display:flex;flex-wrap:wrap;gap:7px}.chip{padding:6px 8px;border-radius:8px;border:1px solid var(--line);background:#0a1a21;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px}.chip.ok{border-color:#245c43;color:var(--ok)}.chip.no{border-color:#6b333c;color:var(--deny)}.pending{display:grid;gap:9px}.ask{border:1px solid #675626;background:#2b2515;border-radius:12px;padding:11px}.ask .title{color:var(--ask);font-weight:750}.ask code{font-size:11px;color:#d8e6e9}.askBtns{display:flex;gap:7px;margin-top:10px}.timeline{max-height:440px;overflow:auto;display:grid;gap:7px}.event{display:grid;grid-template-columns:64px 115px 1fr;gap:8px;padding:8px;border:1px solid #1c3741;border-radius:9px;background:#09181e}.seq{color:#587c85}.eventName{font-weight:700}.eventData{color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.workspace{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;display:grid;gap:8px}.kv{display:grid;grid-template-columns:135px 1fr;gap:8px}.kv span:first-child{color:var(--muted)}.status{display:flex;align-items:center;gap:7px;color:var(--ok)}.dot{width:8px;height:8px;border-radius:50%;background:currentColor;box-shadow:0 0 16px currentColor}.feed{display:grid;gap:7px;margin-top:12px}.notice{padding:9px 10px;border-radius:9px;border:1px solid var(--line);background:#09181e;color:var(--muted)}.notice.ask{color:var(--ask);border-color:#675626}.notice.deny{color:var(--deny);border-color:#6b333c}.notice.ok{color:var(--ok);border-color:#245c43}@media(max-width:900px){.grid,.two{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,1fr)}.shell{padding:12px}.top{align-items:flex-start}.event{grid-template-columns:48px 95px 1fr}.kv{grid-template-columns:110px 1fr}}
</style>
</head>
<body>
<div class="shell">
  <div class="top">
    <div class="brand"><div class="mark">OA</div><div><h1>OnlyAsk</h1><div class="sub">Governed autonomous operations · judge demo console</div></div></div>
    <div class="badge">Strands-ready authority boundary · deterministic demo mode</div>
  </div>
  <div class="grid">
    <section>
      <div class="panel">
        <div class="hd"><strong>Mission</strong><span class="status"><i class="dot"></i><span id="chain">evidence chain valid</span></span></div>
        <div class="body">
          <p class="objective" id="objective"></p>
          <div class="actions">
            <button class="btn primary" onclick="runShowcase()">Run end-to-end showcase</button>
            <button class="btn" onclick="act('inspect')">Inspect site</button>
            <button class="btn" onclick="act('repair')">Repair contact link</button>
            <button class="btn warn" onclick="priceAsk()">Change price → ask</button>
            <button class="btn danger" onclick="act('dns')">Attempt DNS change</button>
            <button class="btn" onclick="act('bad-repair')">Test failed repair + recovery</button>
            <button class="btn" onclick="act('observe')">Inject hostile page instruction</button>
            <button class="btn" onclick="resetDemo()">Reset</button>
          </div>
          <div class="stats">
            <div class="stat"><b id="completed">0</b><span>completed</span></div>
            <div class="stat"><b id="asks">0</b><span>human asks</span></div>
            <div class="stat"><b id="denied">0</b><span>denied</span></div>
            <div class="stat"><b id="recovered">0</b><span>recovered</span></div>
          </div>
          <div id="feed" class="feed"></div>
        </div>
      </div>
      <div class="two">
        <div class="panel"><div class="hd"><strong>Authority envelope</strong></div><div class="body"><div class="sub">ALLOW</div><div id="allow" class="rules"></div><div class="sub" style="margin-top:12px">DENY</div><div id="deny" class="rules"></div></div></div>
        <div class="panel"><div class="hd"><strong>Current workspace</strong></div><div class="body workspace"><div class="kv"><span>checkout price</span><span id="price"></span></div><div class="kv"><span>DNS target</span><span id="dns"></span></div><div class="kv"><span>homepage</span><span id="home"></span></div></div></div>
      </div>
    </section>
    <aside>
      <div class="panel" style="margin-bottom:14px"><div class="hd"><strong>Only ask the human when authority is missing</strong><span id="pendingCount" class="sub"></span></div><div class="body"><div id="pending" class="pending"><div class="sub">No human decision needed.</div></div></div></div>
      <div class="panel"><div class="hd"><strong>Evidence ledger</strong><span id="ledgerCount" class="sub"></span></div><div class="body"><div id="timeline" class="timeline"></div></div></div>
    </aside>
  </div>
</div>
<script>
const $=id=>document.getElementById(id);
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
async function api(path,body){const r=await fetch(path,{method:body?'POST':'GET',headers:{'content-type':'application/json'},body:body?JSON.stringify(body):undefined});const j=await r.json();if(!r.ok)throw new Error(j.error||'request failed');return j}
function note(text,kind='ok'){const el=document.createElement('div');el.className='notice '+kind;el.textContent=text;$('feed').prepend(el);while($('feed').children.length>5)$('feed').lastChild.remove()}
function resultNote(r){if(!r)return;if(r.state==='escalated')note('Human decision required: '+r.message,'ask');else if(r.state==='denied')note('Denied: '+r.message,'deny');else if(r.state==='recovered')note('Verification failed; prior state recovered.','ok');else if(r.disposition==='untrusted_evidence')note('Hostile directive isolated as untrusted evidence.','ok');else note((r.message||r.state||'Completed')+'.','ok')}
async function refresh(){const s=await api('/api/state');$('objective').textContent=s.objective;$('completed').textContent=s.metrics.completed;$('asks').textContent=s.metrics.asks;$('denied').textContent=s.metrics.denied;$('recovered').textContent=s.metrics.recovered;$('price').textContent='$'+s.workspace.checkout_price;$('dns').textContent=s.workspace.dns_target;$('home').textContent=s.workspace.homepage_html;$('chain').textContent=s.ledger_valid?'evidence chain valid':'evidence chain invalid';$('allow').innerHTML=s.authority.allow.map(x=>`<span class="chip ok">${esc(x.resource)} · ${esc(x.action)}</span>`).join('');$('deny').innerHTML=s.authority.deny.map(x=>`<span class="chip no">${esc(x.resource)} · ${esc(x.action)}</span>`).join('');$('pendingCount').textContent=s.pending.length?`${s.pending.length} decision${s.pending.length>1?'s':''}`:'';$('pending').innerHTML=s.pending.length?s.pending.map(p=>`<div class="ask"><div class="title">Human authority required</div><div>${esc(p.purpose)}</div><code>${esc(p.resource)} · ${esc(p.operation)}</code><div class="askBtns"><button class="btn warn" onclick="approve('${esc(p.transition_id)}')">Approve once</button><button class="btn danger" onclick="rejectAsk('${esc(p.transition_id)}')">Decline</button></div></div>`).join(''):'<div class="sub">No human decision needed.</div>';$('ledgerCount').textContent=`${s.ledger.length} events`;$('timeline').innerHTML=[...s.ledger].reverse().map(e=>`<div class="event"><span class="seq">#${e.sequence}</span><span class="eventName">${esc(e.event)}</span><span class="eventData">${esc(JSON.stringify(e.data))}</span></div>`).join('')||'<div class="sub">No transitions yet.</div>'}
async function act(action){try{const r=await api('/api/action',{action});resultNote(r);await refresh()}catch(e){note(e.message,'deny')}}
async function priceAsk(){try{const r=await api('/api/action',{action:'price',new_price:'39.00'});resultNote(r);await refresh()}catch(e){note(e.message,'deny')}}
async function approve(id){try{const r=await api('/api/approve',{transition_id:id});resultNote(r);await refresh()}catch(e){note(e.message,'deny')}}
async function rejectAsk(id){try{const r=await api('/api/reject',{transition_id:id});resultNote(r);await refresh()}catch(e){note(e.message,'deny')}}
async function runShowcase(){try{const r=await api('/api/showcase',{});r.results.forEach(resultNote);await refresh()}catch(e){note(e.message,'deny')}}
async function resetDemo(){try{await api('/api/reset',{});$('feed').innerHTML='';note('Fresh governed session created.');await refresh()}catch(e){note(e.message,'deny')}}
refresh().catch(e=>note(e.message,'deny'));
</script>
</body>
</html>'''


class OnlyAskConsole:
    def __init__(self) -> None:
        self.session = OnlyAskProductSession()
        self.lock = RLock()

    def reset(self) -> dict[str, Any]:
        with self.lock:
            self.session = OnlyAskProductSession()
            return self.session.state()

    def state(self) -> dict[str, Any]:
        with self.lock:
            return self.session.state()

    def showcase(self) -> dict[str, Any]:
        with self.lock:
            return {"results": self.session.run_showcase(), "state": self.session.state()}

    def action(self, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            if name == "inspect":
                result = self.session.inspect_homepage()
                return self.session.result_dict(result)
            if name == "repair":
                result = self.session.repair_contact_link()
                return self.session.result_dict(result)
            if name == "price":
                new_price = str(payload.get("new_price", "39.00")).strip()
                if not new_price or len(new_price) > 16:
                    raise ValueError("Invalid price value")
                result = self.session.request_price_change(new_price)
                return self.session.result_dict(result)
            if name == "dns":
                result = self.session.attempt_dns_change()
                return self.session.result_dict(result)
            if name == "bad-repair":
                result = self.session.simulate_failed_repair()
                return self.session.result_dict(result)
            if name == "observe":
                return self.session.observe_external_directive()
            raise ValueError(f"Unknown action: {name}")

    def approve(self, transition_id: str) -> dict[str, Any]:
        with self.lock:
            if transition_id not in self.session.pending:
                raise KeyError("Pending transition not found")
            return self.session.result_dict(self.session.approve_once(transition_id))

    def reject(self, transition_id: str) -> dict[str, Any]:
        with self.lock:
            if transition_id not in self.session.pending:
                raise KeyError("Pending transition not found")
            return self.session.reject(transition_id)


def make_handler(console: OnlyAskConsole) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "OnlyAsk/0.2"

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, default=str).encode("utf-8")
            self.send_response(status.value)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 16_384:
                raise ValueError("Request body too large")
            raw = self.rfile.read(length) if length else b"{}"
            value = json.loads(raw.decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError("JSON object required")
            return value

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/":
                body = PAGE.encode("utf-8")
                self.send_response(HTTPStatus.OK.value)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.end_headers()
                self.wfile.write(body)
                return
            if path == "/api/state":
                self._json(HTTPStatus.OK, console.state())
                return
            self._json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            try:
                payload = self._read_json()
                if path == "/api/reset":
                    self._json(HTTPStatus.OK, console.reset())
                    return
                if path == "/api/showcase":
                    self._json(HTTPStatus.OK, console.showcase())
                    return
                if path == "/api/action":
                    self._json(HTTPStatus.OK, console.action(str(payload.get("action", "")), payload))
                    return
                if path == "/api/approve":
                    self._json(HTTPStatus.OK, console.approve(str(payload.get("transition_id", ""))))
                    return
                if path == "/api/reject":
                    self._json(HTTPStatus.OK, console.reject(str(payload.get("transition_id", ""))))
                    return
                self._json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            except (ValueError, json.JSONDecodeError) as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            except KeyError as exc:
                self._json(HTTPStatus.NOT_FOUND, {"error": str(exc)})

    return Handler


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    if not 1 <= port <= 65535:
        raise ValueError("port must be between 1 and 65535")
    console = OnlyAskConsole()
    server = ThreadingHTTPServer((host, port), make_handler(console))
    print(f"OnlyAsk console: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
