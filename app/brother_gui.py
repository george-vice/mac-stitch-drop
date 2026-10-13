#!/usr/bin/env python3
"""StitchDrop — drag-and-drop sender for Brother Wi-Fi embroidery machines.

Runs a tiny web app on your own Mac (127.0.0.1 only) and opens it in your
browser. Needs brother_send.py in the same folder. Python 3 stdlib only.
"""
import http.server
import json
import os
import sys
import tempfile
import threading
import time
import urllib.request
import urllib.parse
import webbrowser
import concurrent.futures as cf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brother_send as bs  # noqa: E402

CONFIG = os.path.expanduser("~/.stitchdrop.json")
PORT = int(os.environ.get("STITCHDROP_PORT", "47821"))
_last_ping = [None]          # set by the page's heartbeat
_started = time.time()


def load_cfg():
    try:
        with open(CONFIG) as f:
            return json.load(f)
    except Exception:
        return {}


def save_cfg(cfg):
    try:
        with open(CONFIG, "w") as f:
            json.dump(cfg, f)
    except OSError:
        pass


def scan_quiet():
    hosts = [str(h) for n in bs._local_subnets() for h in n.hosts()]
    found = []
    with cf.ThreadPoolExecutor(64) as pool:
        for hit in pool.map(bs._probe, hosts):
            if hit:
                ip, info = hit
                found.append({"ip": ip, "name": info.get("name") or "Brother machine",
                              "version": info.get("version")})
    return found


PAGE = r"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>StitchDrop</title>
<style>
:root{--bg:#f6f4ef;--card:#fff;--ink:#22201c;--mute:#7a746a;--line:#e3ded4;--acc:#2f6f5e;--ok:#2f6f5e;--err:#b0412e}
@media (prefers-color-scheme:dark){:root{--bg:#191816;--card:#23211e;--ink:#eeeae2;--mute:#9b9488;--line:#36332e;--acc:#6cbfa6;--ok:#6cbfa6;--err:#e07a64}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 -apple-system,BlinkMacSystemFont,"SF Pro Text",sans-serif}
main{max-width:560px;margin:40px auto;padding:0 16px}
h1{font-size:22px;margin:0 0 4px;letter-spacing:-.01em}.sub{color:var(--mute);margin:0 0 22px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin-bottom:14px}
.row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.dot{width:9px;height:9px;border-radius:50%;background:var(--mute)}.dot.on{background:var(--ok)}.dot.bad{background:var(--err)}
.grow{flex:1;min-width:0}.mute{color:var(--mute);font-size:13px}
button{font:inherit;border:1px solid var(--line);background:transparent;color:var(--ink);border-radius:8px;padding:6px 12px;cursor:pointer}
button:hover{border-color:var(--acc)}button:disabled{opacity:.5;cursor:default}
input{font:inherit;background:transparent;color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:6px 10px;width:150px}
select{font:inherit;background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:6px}
#drop{border:2px dashed var(--line);border-radius:14px;padding:44px 16px;text-align:center;cursor:pointer;transition:.15s}
#drop.hover{border-color:var(--acc);background:color-mix(in srgb,var(--acc) 8%,transparent)}
#drop b{display:block;font-size:17px;margin-bottom:4px}
ul{list-style:none;margin:0;padding:0}li{display:flex;gap:10px;padding:8px 0;border-top:1px solid var(--line)}li:first-child{border-top:0}
.st{margin-left:auto;font-size:13px;white-space:nowrap}.st.ok{color:var(--ok)}.st.err{color:var(--err)}
.bar{height:6px;background:var(--line);border-radius:3px;overflow:hidden;margin-top:8px}.bar i{display:block;height:100%;background:var(--acc)}
</style></head><body><main>
<div class="row"><h1 class="grow">StitchDrop</h1><button id="quit">Quit</button></div><p class="sub">Send embroidery files to your Brother machine over Wi‑Fi.</p>

<div class="card">
 <div class="row"><span id="dot" class="dot"></span>
  <div class="grow"><div id="mname">Looking for your machine…</div><div id="mdetail" class="mute"></div></div>
  <select id="pick" hidden></select>
  <button id="scan">Scan</button></div>
 <div class="row" style="margin-top:10px"><span class="mute">Or enter IP:</span>
  <input id="ip" placeholder="192.168.1.50"><button id="useip">Connect</button></div>
 <div id="mem" hidden><div class="bar"><i id="memfill"></i></div><div id="memtxt" class="mute" style="margin-top:4px"></div></div>
</div>

<div id="drop" class="card"><b>Drop .pes files here</b><span class="mute">or click to choose · also .phc .phx .dst .pen</span>
 <input id="file" type="file" multiple accept=".pes,.phc,.phx,.dst,.pen" hidden></div>

<div class="card" id="logcard" hidden><ul id="log"></ul></div>
</main><script>
const $=id=>document.getElementById(id);let ip=null;
async function api(p,o){const r=await fetch(p,o);const j=await r.json();if(!r.ok)throw new Error(j.error||r.statusText);return j}
function setMachine(m){ip=m.ip;$('dot').className='dot on';$('mname').textContent=m.name;$('mdetail').textContent=m.ip+(m.version?' · firmware '+m.version:'');refresh()}
async function refresh(){if(!ip)return;try{const s=await api('/api/status?ip='+ip);$('mem').hidden=false;
 const used=s.total-s.free;$('memfill').style.width=(s.total?100*used/s.total:0)+'%';
 $('memtxt').textContent=`${(s.free/1024).toFixed(0)} KB free · ${s.files.length} design${s.files.length==1?'':'s'} on machine`}
 catch(e){$('dot').className='dot bad';$('mdetail').textContent=ip+' · '+e.message}}
async function scan(){$('scan').disabled=true;$('dot').className='dot';$('mname').textContent='Scanning your network…';$('mdetail').textContent='Takes a few seconds';
 try{const r=await api('/api/scan');$('pick').hidden=r.machines.length<2;
  if(r.machines.length){$('pick').innerHTML=r.machines.map((m,i)=>`<option value="${i}">${m.name} (${m.ip})</option>`).join('');
   $('pick').onchange=()=>setMachine(r.machines[$('pick').value]);setMachine(r.machines[0])}
  else{$('dot').className='dot bad';$('mname').textContent='No machine found';$('mdetail').textContent='Is it on, and on the same Wi‑Fi? Try entering its IP.'}}
 catch(e){$('mname').textContent='Scan failed';$('mdetail').textContent=e.message}$('scan').disabled=false}
async function connectIp(v){$('mname').textContent='Connecting…';try{setMachine(await api('/api/connect?ip='+encodeURIComponent(v)))}
 catch(e){$('dot').className='dot bad';$('mname').textContent='Not reachable';$('mdetail').textContent=e.message}}
async function send(files){if(!ip){alert('Find your machine first.');return}$('logcard').hidden=false;
 for(const f of files){const li=document.createElement('li');li.innerHTML=`<span></span><span class="st">Sending…</span>`;
  li.firstChild.textContent=f.name;$('log').prepend(li);const st=li.lastChild;
  try{await api(`/api/send?ip=${ip}&name=${encodeURIComponent(f.name)}`,{method:'POST',body:await f.arrayBuffer()});st.textContent='Sent ✓';st.className='st ok'}
  catch(e){st.textContent=e.message;st.className='st err'}}refresh()}
const d=$('drop');d.onclick=()=>$('file').click();$('file').onchange=e=>{send([...e.target.files]);e.target.value=''};
['dragenter','dragover'].forEach(t=>d.addEventListener(t,e=>{e.preventDefault();d.classList.add('hover')}));
['dragleave','drop'].forEach(t=>d.addEventListener(t,e=>{e.preventDefault();d.classList.remove('hover')}));
d.addEventListener('drop',e=>send([...e.dataTransfer.files]));
window.addEventListener('dragover',e=>e.preventDefault());window.addEventListener('drop',e=>e.preventDefault());
$('scan').onclick=scan;setInterval(()=>fetch('/api/ping').catch(()=>{}),10000);fetch('/api/ping');
$('quit').onclick=async()=>{await fetch('/api/quit').catch(()=>{});document.body.innerHTML='<main><h1>StitchDrop has quit.</h1><p class=sub>You can close this tab.</p></main>'};$('useip').onclick=()=>connectIp($('ip').value.trim());
(async()=>{const c=await api('/api/config');if(c.ip){$('ip').value=c.ip;await connectIp(c.ip);if(ip)return}scan()})();
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _q(self):
        return {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).items()}

    def _local_only(self):
        # Block other websites from driving this server via the browser.
        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost"):
            self._json({"error": "forbidden"}, 403)
            return False
        return True

    def do_GET(self):
        if not self._local_only():
            return
        path = urllib.parse.urlparse(self.path).path
        q = self._q()
        try:
            if path == "/":
                b = PAGE.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)
            elif path == "/api/ping":
                _last_ping[0] = time.time()
                self._json({"ok": True})
            elif path == "/api/quit":
                self._json({"ok": True})
                threading.Timer(0.3, os._exit, [0]).start()
            elif path == "/api/config":
                self._json(load_cfg())
            elif path == "/api/scan":
                machines = scan_quiet()
                if machines:
                    save_cfg({"ip": machines[0]["ip"]})
                self._json({"machines": machines})
            elif path == "/api/connect":
                info = bs.get_info(q["ip"], timeout=4)
                if "pedxml" not in info.get("apis", {}):
                    raise RuntimeError("that device doesn't speak Brother's transfer protocol")
                save_cfg({"ip": q["ip"]})
                self._json({"ip": q["ip"], "name": info.get("name") or "Brother machine",
                            "version": info.get("version")})
            elif path == "/api/status":
                self._json(bs.get_status(q["ip"]))
            else:
                self._json({"error": "not found"}, 404)
        except Exception as e:
            self._json({"error": str(e) or e.__class__.__name__}, 502)

    def do_POST(self):
        if not self._local_only():
            return
        if urllib.parse.urlparse(self.path).path != "/api/send":
            return self._json({"error": "not found"}, 404)
        q = self._q()
        name = os.path.basename(q.get("name", "design.pes"))
        ext = os.path.splitext(name)[1].lower()
        if ext not in bs.EXTS:
            return self._json({"error": f"{ext or 'that file'} isn't a machine format"}, 400)
        data = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            free = bs.get_status(q["ip"])["free"]
            if len(data) > free:
                return self._json({"error": f"not enough memory ({free // 1024} KB free)"}, 400)
            with tempfile.TemporaryDirectory() as d:
                p = os.path.join(d, name)
                with open(p, "wb") as f:
                    f.write(data)
                bs.send_file(q["ip"], p)
            self._json({"ok": True})
        except Exception as e:
            self._json({"error": str(e) or e.__class__.__name__}, 502)


def _already_running():
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/config", timeout=1):
            return True
    except Exception:
        return False


def _watchdog():
    """Quit when the browser tab has been closed (no heartbeat for 45 s),
    or after 5 min if no tab ever connected."""
    while True:
        time.sleep(5)
        last = _last_ping[0]
        if (last and time.time() - last > 45) or (not last and time.time() - _started > 300):
            os._exit(0)


def main():
    url = f"http://127.0.0.1:{PORT}/"
    if _already_running():
        webbrowser.open(url)           # second double-click: just show it
        return
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"StitchDrop running at {url}")
    if not os.environ.get("STITCHDROP_NO_BROWSER"):
        threading.Timer(0.5, webbrowser.open, [url]).start()
    if not os.environ.get("STITCHDROP_NO_WATCHDOG"):
        threading.Thread(target=_watchdog, daemon=True).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
