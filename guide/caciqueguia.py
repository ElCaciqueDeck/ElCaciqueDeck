#!/usr/bin/env python3
"""
ElCaciqueDeck - CaciqueGuía: a chat page where the family asks the LOCAL AI how to care for and fix the Home Lab.

  python3 ~/elcaciquedeck/guide/caciqueguia.py        (start-all.sh starts it; port 8070)
  Open: http://<laptop number>:8070

For every question it gives the AI (Ollama, on this same computer):
  - what the Home Lab is and its rules (below),
  - the server status right now (status.sh),
  - the logbook (tools/logbook.py brief): recent warnings, errors and daily gauge summaries,
  - the Field Manual sections that match the question (manual/src).
Nothing leaves the house. Only the Python that comes with Ubuntu is needed.
"""
import json, os, re, subprocess, sys, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = int(os.environ.get("GUIDE_PORT", "8070"))
OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")


def env_value(key, default):
    try:
        for line in open(os.path.join(REPO, "guide", ".env")):
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return default


MODEL = os.environ.get("GUIDE_MODEL") or env_value("GUIDE_MODEL", "qwen2.5:3b")

RULES = """You are CaciqueGuía, the helper of "El Cacique Home Lab" (ElCaciqueDeck), a family home server in Puerto Rico
built on Ubuntu by a beginner. Answer ONLY about this Home Lab: how to use it, care for it and fix it.
Reply in the language of the question (Spanish or English), simply, step by step, for a beginner.
Rules of this Home Lab you must respect:
- Terminal commands are typed by hand: give ONE command per line, numbered, in the order to run them.
- Nothing starts by itself at boot unless the owner chose it; servers start with: bash ~/elcaciquedeck/start-all.sh
- Status of everything: bash ~/elcaciquedeck/status.sh . Apply updates: cd ~/elcaciquedeck && git pull, then bash ~/elcaciquedeck/tools/update.sh
- Two drives: Library (media, games, encyclopedia; replaceable) and Vault (documents, photos, passwords; irreplaceable).
- CaciqueDocs Error 500 is usually wrong file owners on Vault: bash ~/elcaciquedeck/tools/fix-docs.sh
- Never suggest deleting data, formatting drives or turning off security without a clear warning first.
- Legal content only (own media, free/homebrew games). Never help with piracy.
- If you are not sure, say so and suggest checking the Field Manual (CaciqueLibrary) or asking the owner.
Apps: CaciqueFlix (Jellyfin 8096), CaciquePhotos (Immich 2283), CaciqueLibrary (Kiwix 8080), CaciqueArcade (RomM 8090),
CaciqueDocs (Paperless 8000), CaciqueAcademy (8095), CaciqueHome (Home Assistant 8123), CaciqueDash (gauges 8888),
CaciqueGuard (AdGuard 3000 + names), CaciqueVault (passwords, https 8443), CaciqueCalendar (5232), CaciqueSync (Syncthing 8384),
CaciqueCams (cameras 8971, recordings deleted after 90 days), CaciqueFinanzas (family budget https 5443, money coach https 5444;
password in ~/elcaciquedeck-data/accounts/finanzas-password.txt), front page on port 80."""


def run(cmd, timeout=60):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except Exception as e:
        return "(could not run: %s)" % e


def manual_sections(question, limit=3):
    """The Field Manual sections whose words match the question best."""
    words = {w for w in re.findall(r"[a-záéíóúñü0-9]{4,}", question.lower())}
    scored = []
    for name in sorted(os.listdir(os.path.join(REPO, "manual", "src"))):
        if not name.endswith(".md"):
            continue
        text = open(os.path.join(REPO, "manual", "src", name), encoding="utf-8").read()
        for part in re.split(r"\n(?=## )", text):
            low = part.lower()
            score = sum(low.count(w) for w in words)
            if score:
                scored.append((score, name, part[:2500]))
    scored.sort(reverse=True)
    return "\n\n".join("[Field Manual %s]\n%s" % (n, p) for _, n, p in scored[:limit]) or "(no matching manual section)"


def context(question):
    status = run(["bash", os.path.join(REPO, "status.sh")], 90)
    book = run([sys.executable, os.path.join(REPO, "tools", "logbook.py"), "brief"], 60)
    return ("SERVER STATUS RIGHT NOW:\n%s\n\nLOGBOOK:\n%s\n\nFIELD MANUAL:\n%s" %
            (status.strip()[-3000:], book.strip()[-5000:], manual_sections(question)))


def ask_ai(question, history):
    msgs = [{"role": "system", "content": RULES}, {"role": "system", "content": context(question)}]
    for h in history[-6:]:
        if h.get("role") in ("user", "assistant") and isinstance(h.get("content"), str):
            msgs.append({"role": h["role"], "content": h["content"][:4000]})
    msgs.append({"role": "user", "content": question})
    body = json.dumps({"model": MODEL, "messages": msgs, "stream": True}).encode()
    req = urllib.request.Request(OLLAMA + "/api/chat", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        for line in r:
            try:
                d = json.loads(line)
            except Exception:
                continue
            piece = d.get("message", {}).get("content", "")
            if piece:
                yield piece
            if d.get("done"):
                break


PAGE = r"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CaciqueGuía</title><style>
:root{--bg:#0b1322;--card:#16213a;--line:#2a3654;--txt:#f5f7fc;--muted:#b6c3d5;--accent:#f6a744}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:16px/1.5 -apple-system,"Segoe UI",Ubuntu,sans-serif}
.wrap{max-width:820px;margin:0 auto;padding:16px;display:flex;flex-direction:column;height:100vh}
h1{margin:4px 0;font-size:22px}h1 span{color:var(--accent)}p.sub{margin:0 0 12px;color:var(--muted);font-size:14px}
#log{flex:1;overflow:auto;display:flex;flex-direction:column;gap:10px;padding-bottom:10px}
.m{padding:10px 14px;border-radius:14px;white-space:pre-wrap;word-break:break-word;max-width:92%}
.u{align-self:flex-end;background:#24375f}.a{align-self:flex-start;background:var(--card);border:1px solid var(--line)}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}.chips button{background:var(--card);border:1px solid var(--line);color:var(--txt);border-radius:999px;padding:6px 12px;font:inherit;font-size:13px;cursor:pointer}
form{display:flex;gap:8px}textarea{flex:1;min-height:52px;max-height:160px;background:var(--card);color:var(--txt);border:1px solid var(--line);border-radius:12px;padding:10px;font:inherit}
form button{background:var(--accent);border:0;border-radius:12px;padding:0 18px;font:600 16px inherit;cursor:pointer;color:#1a1206}
button:focus-visible,textarea:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
</style></head><body><div class="wrap">
<h1>🤖 <span>CaciqueGuía</span></h1>
<p class="sub">Pregúntale cómo cuidar o arreglar El Cacique. Ella lee el estado de los servidores y la bitácora. Todo se queda en la casa. · Ask how to care for or fix the Home Lab. Everything stays at home.</p>
<div class="chips"><button>¿Qué servidores tienen problemas ahora?</button><button>CaciqueDocs dice Error 500, ¿qué hago?</button><button>How do I add a movie to CaciqueFlix?</button><button>¿Cómo conecto una cámara nueva?</button></div>
<div id="log" role="log" aria-live="polite"></div>
<form id="f"><textarea id="q" placeholder="Escribe tu pregunta · Type your question" aria-label="pregunta"></textarea><button>Enviar</button></form>
</div><script>
const log=document.getElementById('log'),q=document.getElementById('q'),hist=[];
function add(cls,t){const d=document.createElement('div');d.className='m '+cls;d.textContent=t;log.append(d);log.scrollTop=log.scrollHeight;return d}
async function send(text){if(!text.trim())return;add('u',text);q.value='';const a=add('a','…');
 try{const r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({q:text,history:hist})});
  const rd=r.body.getReader(),dec=new TextDecoder();let out='';a.textContent='';
  for(;;){const {done,value}=await rd.read();if(done)break;out+=dec.decode(value,{stream:true});a.textContent=out;log.scrollTop=log.scrollHeight}
  hist.push({role:'user',content:text},{role:'assistant',content:out});
 }catch(e){a.textContent='No pude hablar con la IA. ¿Está prendida? (start-all.sh) · Could not reach the AI.'}}
document.getElementById('f').onsubmit=e=>{e.preventDefault();send(q.value)};
q.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send(q.value)}});
document.querySelectorAll('.chips button').forEach(b=>b.onclick=()=>send(b.textContent));
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/health"):
            data = b"ok"
            self.send_response(200)
        else:
            data = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/ask":
            self.send_response(404)
            self.end_headers()
            return
        try:
            req = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            question = str(req.get("q", ""))[:2000]
            history = req.get("history") if isinstance(req.get("history"), list) else []
        except Exception:
            self.send_response(400)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

        def chunk(text):
            b = text.encode()
            self.wfile.write(b"%x\r\n%s\r\n" % (len(b), b))
            self.wfile.flush()
        try:
            for piece in ask_ai(question, history):
                chunk(piece)
        except Exception as e:
            chunk("\n(La IA no contestó · The AI did not answer: %s. ¿Está prendida? bash ~/elcaciquedeck/start-all.sh)" % e)
        try:
            self.wfile.write(b"0\r\n\r\n")
        except Exception:
            pass


def main():
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("CaciqueGuía on port %d (model %s)" % (PORT, MODEL), flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
