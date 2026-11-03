#!/usr/bin/env python3
"""
ElCaciqueDeck - CaciqueFinanzas Coach: reads the family budgets (Actual Budget) and coaches.

  python3 ~/elcaciquedeck/finanzas/caciquefinanzas.py      (start-all.sh starts it; listens inside the laptop on 8075)
  Open: https://<laptop number>:5444   (Caddy's secure door; password = the family budget password)

What it does, from the budget numbers only:
  - Year-end forecast: "at this pace you finish the year at ..." and the same with extra weekly savings.
  - This month by category: budgeted, spent, left, how many times, and over-limit alerts.
  - Count limits the family sets here ("Eating out: max 4 times a month") on top of Actual's $ budgets.
  - Optional: a written report and questions answered by the local AI (CaciqueGuía's Ollama), if installed.
It coaches budgeting from the family's own numbers. It never gives investment advice. Nothing leaves the house.
Only the Python that comes with Ubuntu is needed.
"""
import calendar, datetime as dt, hmac, json, os, secrets, sys, threading, time, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(os.path.expanduser("~"), "elcaciquedeck-data", "finanzas")
RULES_FILE = os.path.join(DATA, "rules.json")
PORT = int(os.environ.get("FINANZAS_PORT", "8075"))
BIND = os.environ.get("FINANZAS_BIND", "127.0.0.1")
API = os.environ.get("FINANZAS_API", "http://127.0.0.1:5007/v1")
OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
SESSIONS, LOCK = {}, threading.Lock()


def env_value(path, key, default=""):
    try:
        for line in open(path, encoding="utf-8"):
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return default


ENV = os.path.join(REPO, "finanzas", ".env")
PASSWORD = os.environ.get("FINANZAS_PASSWORD") or env_value(ENV, "FINANZAS_PASSWORD")
API_KEY = os.environ.get("FINANZAS_API_KEY") or env_value(ENV, "FINANZAS_API_KEY")
MODEL = os.environ.get("GUIDE_MODEL") or env_value(os.path.join(REPO, "guide", ".env"), "GUIDE_MODEL", "qwen2.5:3b")


# ================================================================ reading the budgets
def api(path, timeout=60):
    req = urllib.request.Request(API + path, headers={"x-api-key": API_KEY})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode()).get("data")


def budgets():
    seen, out = set(), []
    for b in api("/budgets") or []:
        gid = b.get("groupId")
        if gid and gid not in seen and b.get("state") != "broken":
            seen.add(gid)
            out.append({"id": gid, "name": b.get("name") or "Budget", "encrypted": bool(b.get("encryptKeyId"))})
    return out


def money(cents):
    return round((cents or 0) / 100.0, 2)


def flat(transactions):
    """Real spending/income lines: splits opened up, transfers between own accounts left out."""
    for t in transactions or []:
        subs = t.get("subtransactions") or []
        for s in (subs if subs else [t]):
            if s.get("transfer_id") or t.get("transfer_id"):
                continue
            yield {"date": t.get("date"), "amount": s.get("amount") or 0, "category": s.get("category"),
                   "payee": s.get("payee") or t.get("payee")}


def load_rules():
    try:
        return json.load(open(RULES_FILE, encoding="utf-8"))
    except Exception:
        return {}


def save_rules(rules):
    os.makedirs(DATA, exist_ok=True)
    tmp = RULES_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=2)
    os.replace(tmp, RULES_FILE)


def summary(budget_id, today=None):
    today = today or dt.date.today()
    q = "/budgets/" + urllib.parse.quote(budget_id)
    accounts = [a for a in (api(q + "/accounts") or []) if not a.get("closed")]
    on_budget = [a for a in accounts if not a.get("offbudget")]
    cats = {c["id"]: c for c in (api(q + "/categories") or [])}
    month = today.strftime("%Y-%m")
    month_cats = api(q + "/months/%s/categories" % month) or []

    cash = 0
    for a in on_budget:
        try:
            cash += api(q + "/accounts/%s/balance" % a["id"]) or 0
        except Exception:
            pass

    # last 3 full months + this month of transactions
    first_this = today.replace(day=1)
    start = (first_this - dt.timedelta(days=1)).replace(day=1)
    for _ in range(2):
        start = (start - dt.timedelta(days=1)).replace(day=1)
    lines = []
    for a in on_budget:
        try:
            lines += list(flat(api(q + "/accounts/%s/transactions?since_date=%s" % (a["id"], start.isoformat()))))
        except Exception:
            pass

    # monthly net (income - spending) for the 3 full months before this one
    nets = {}
    for t in lines:
        m = (t["date"] or "")[:7]
        if m and m < month:
            nets[m] = nets.get(m, 0) + t["amount"]
    full = [nets.get(m, 0) for m in sorted(nets)][-3:]
    avg_net = sum(full) / len(full) if full else 0

    # this month: times per category
    times = {}
    for t in lines:
        if (t["date"] or "")[:7] == month and t["amount"] < 0 and t["category"]:
            times[t["category"]] = times.get(t["category"], 0) + 1

    rules = load_rules().get(budget_id, {}).get("max_times", {})
    rows, alerts = [], []
    day, mdays = today.day, calendar.monthrange(today.year, today.month)[1]
    for c in month_cats:
        info = cats.get(c.get("id"), {})
        if c.get("is_income") or info.get("is_income") or c.get("hidden"):
            continue
        budgeted, spent = money(c.get("budgeted")), money(-(c.get("spent") or 0))
        count, limit = times.get(c.get("id"), 0), rules.get(c.get("name"))
        if budgeted > 0 and spent > budgeted:
            status = "over"
            alerts.append({"level": "over", "category": c.get("name"),
                           "text_en": "%s: $%.2f spent of your $%.2f limit (+$%.2f over)." % (c.get("name"), spent, budgeted, spent - budgeted),
                           "text_es": "%s: gastaste $%.2f de tu límite de $%.2f (+$%.2f de más)." % (c.get("name"), spent, budgeted, spent - budgeted)})
        elif budgeted > 0 and spent >= 0.8 * budgeted:
            status = "near"
        elif budgeted > 0:
            status = "ok"
        else:
            status = "none" if spent == 0 else "unplanned"
        if limit and count > limit:
            status = "over"
            alerts.append({"level": "over", "category": c.get("name"),
                           "text_en": "%s: %d times this month. You set a limit of %d." % (c.get("name"), count, limit),
                           "text_es": "%s: %d veces este mes. Tu límite es %d." % (c.get("name"), count, limit)})
        elif limit and count == limit:
            alerts.append({"level": "near", "category": c.get("name"),
                           "text_en": "%s: %d of %d times used. The next one goes over." % (c.get("name"), count, limit),
                           "text_es": "%s: usaste %d de %d veces. La próxima se pasa." % (c.get("name"), count, limit)})
        if budgeted > 0 and status != "over" and day >= 5:
            pace = spent / day * mdays
            if pace > budgeted * 1.1:
                alerts.append({"level": "near", "category": c.get("name"),
                               "text_en": "%s: at this pace you reach $%.0f by month's end (limit $%.0f)." % (c.get("name"), pace, budgeted),
                               "text_es": "%s: a este ritmo llegas a $%.0f al final del mes (límite $%.0f)." % (c.get("name"), pace, budgeted)})
        rows.append({"id": c.get("id"), "name": c.get("name"), "budgeted": budgeted, "spent": spent,
                     "left": money(c.get("balance")), "times": count, "max_times": limit, "status": status})
    rows.sort(key=lambda r: ({"over": 0, "near": 1, "unplanned": 2, "ok": 3, "none": 4}[r["status"]], -r["spent"]))

    year_end = dt.date(today.year, 12, 31)
    days_left = (year_end - today).days
    return {
        "budget": budget_id, "month": month, "today": today.isoformat(),
        "cash": money(cash), "avg_net": money(avg_net), "months_used": len(full),
        "months_left": round(days_left / 30.44, 2), "weeks_left": round(days_left / 7.0, 1),
        "year_end": money(cash + avg_net * days_left / 30.44),
        "accounts": [a.get("name") for a in on_budget],
        "categories": rows, "alerts": alerts,
        "spent_month": round(sum(r["spent"] for r in rows), 2),
        "budgeted_month": round(sum(r["budgeted"] for r in rows), 2),
    }


# ================================================================ the AI coach (optional)
COACH = """You are the money coach of a Puerto Rico family's home server (CaciqueFinanzas).
Reply in the language of the question (Spanish or English), warm, short and practical, for a beginner.
Use ONLY the numbers given below; never invent amounts. Name the category and the amount when you correct a habit.
Point out over-limit categories kindly, say what to change this week, and show the year-end difference saving would make.
You coach budgeting and saving only: never recommend investments, stocks, crypto, loans or specific financial products;
for those, suggest talking with a licensed professional. Never shame anyone."""


def ai_available():
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def facts(s):
    lines = ["Today %s. Cash in on-budget accounts: $%.2f." % (s["today"], s["cash"]),
             "Average monthly net (income minus spending) over the last %d months: $%.2f." % (s["months_used"], s["avg_net"]),
             "Forecast at this pace for December 31: $%.2f (%.1f months left)." % (s["year_end"], s["months_left"]),
             "This month: $%.2f spent of $%.2f budgeted." % (s["spent_month"], s["budgeted_month"])]
    for r in s["categories"]:
        if r["spent"] or r["budgeted"]:
            lines.append("- %s: spent $%.2f of $%.2f budgeted, %d purchases%s, status %s." % (
                r["name"], r["spent"], r["budgeted"], r["times"],
                " (limit %d times)" % r["max_times"] if r["max_times"] else "", r["status"]))
    for a in s["alerts"]:
        lines.append("ALERT: " + a["text_en"])
    return "\n".join(lines)


def ask_ai(question, s):
    msgs = [{"role": "system", "content": COACH}, {"role": "system", "content": "BUDGET NUMBERS:\n" + facts(s)},
            {"role": "user", "content": question}]
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


# ================================================================ the page
PAGE = r"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CaciqueFinanzas</title><style>
:root{--bg:#0b1322;--card:#16213a;--line:#2a3654;--txt:#f5f7fc;--muted:#b6c3d5;--accent:#f6a744;--good:#4cc38a;--warn:#f2c94c;--bad:#ff6b6b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:15px/1.5 -apple-system,"Segoe UI",Ubuntu,sans-serif}
.wrap{max-width:980px;margin:0 auto;padding:16px;display:grid;gap:16px}
h1{margin:0;font-size:24px}h1 span{color:var(--accent)}h2{margin:0 0 8px;font-size:17px}
.sub{color:var(--muted);margin:0;font-size:14px}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.row{display:flex;flex-wrap:wrap;gap:12px;align-items:center}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
.big{font-size:28px;font-weight:700;font-variant-numeric:tabular-nums}.lab{color:var(--muted);font-size:13px}
.pos{color:var(--good)}.neg{color:var(--bad)}
select,input,button,textarea{font:inherit;color:var(--txt);background:#0f1a30;border:1px solid var(--line);border-radius:10px;padding:8px 10px}
button{background:var(--accent);color:#1a1206;border:0;font-weight:600;cursor:pointer}button.ghost{background:transparent;color:var(--txt);border:1px solid var(--line)}
:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.alert{padding:10px 12px;border-radius:10px;border-left:5px solid var(--warn);background:#1d2a47;margin-top:8px}.alert.over{border-color:var(--bad)}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}th,td{padding:8px 6px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left;white-space:normal}th{color:var(--muted);font-weight:500;font-size:13px}
.pill{padding:2px 8px;border-radius:999px;font-size:12px;font-weight:700}.over{color:var(--bad)}.near{color:var(--warn)}.ok{color:var(--good)}.none,.unplanned{color:var(--muted)}
.scroll{overflow-x:auto}#coach{white-space:pre-wrap;min-height:40px}svg text{fill:var(--muted);font-size:11px}
#login{max-width:360px;margin:12vh auto;display:grid;gap:10px}
[hidden]{display:none!important}.wrap>*,.grid>*{min-width:0}
</style></head><body>
<div id="login" class="card" hidden><h1>💰 <span>CaciqueFinanzas</span></h1><p class="sub">Contraseña del presupuesto de la familia · Family budget password</p>
<form id="lf" class="row"><input id="pw" type="password" autocomplete="current-password" aria-label="password" style="flex:1"><button>Entrar</button></form><p id="lerr" class="sub"></p></div>
<div id="app" class="wrap" hidden>
 <div class="row" style="justify-content:space-between"><div><h1>💰 <span>CaciqueFinanzas</span></h1>
  <p class="sub">Tu coach de dinero. Solo usa los números de tu presupuesto y nada sale de la casa. · Your money coach, from your own budget numbers.</p></div>
  <div class="row"><label class="lab" for="bud">Presupuesto</label><select id="bud"></select><button class="ghost" id="refresh">↻</button></div></div>
 <p id="msg" class="sub"></p>
 <div class="grid">
  <div class="card"><div class="lab">Dinero hoy · Cash today</div><div class="big" id="cash">—</div></div>
  <div class="card"><div class="lab">Promedio por mes · Avg per month</div><div class="big" id="net">—</div></div>
  <div class="card"><div class="lab">31 de diciembre a este ritmo · Dec 31 at this pace</div><div class="big" id="ye">—</div></div>
 </div>
 <div class="card"><h2>¿Y si ahorras más? · What if you save more?</h2>
  <div class="row"><label for="save" class="lab">Ahorro extra por semana · Extra savings per week</label><input id="save" type="range" min="0" max="300" step="5" value="25" style="flex:1;min-width:160px"><b id="saveL">$25</b></div>
  <p id="saveTxt" style="margin:8px 0 4px"></p><svg id="chart" viewBox="0 0 600 180" style="width:100%;height:auto" role="img" aria-label="forecast"></svg></div>
 <div class="card"><h2>Alertas · Alerts</h2><div id="alerts"></div></div>
 <div class="card"><h2>Este mes · This month</h2><div class="scroll"><table><thead><tr><th>Categoría</th><th>Límite $</th><th>Gastado</th><th>Queda</th><th>Veces</th><th>Máx. veces</th><th></th></tr></thead><tbody id="rows"></tbody></table></div>
  <p class="sub">"Límite $" sale de tu presupuesto en Actual. "Máx. veces" lo pones aquí (ej. Comer fuera: 4). · $ limits come from Actual; set max times here.</p></div>
 <div class="card"><h2>Coach (IA local)</h2><div class="row"><button id="report">Informe del mes · Monthly report</button><input id="q" placeholder="Pregunta · Ask" style="flex:1;min-width:180px"><button class="ghost" id="ask">Enviar</button></div>
  <div id="coach" style="margin-top:10px"></div></div>
</div>
<script>
const $=id=>document.getElementById(id);const f=n=>(n<0?'−':'')+'$'+Math.abs(n).toLocaleString('en-US',{maximumFractionDigits:0});
let S=null;
async function j(u,o){const r=await fetch(u,o);if(r.status===401){show(false);throw new Error('login')}const d=await r.json();if(!r.ok)throw new Error(d.error||r.status);return d}
function show(ok){$('login').hidden=ok;$('app').hidden=!ok}
$('lf').onsubmit=async e=>{e.preventDefault();const r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:$('pw').value})});
 if(r.ok){$('pw').value='';start()}else{$('lerr').textContent='Contraseña incorrecta · Wrong password'}};
async function start(){try{const b=await j('/api/budgets');show(true);$('bud').innerHTML=b.map(x=>`<option value="${x.id}">${x.name}${x.encrypted?' 🔒':''}</option>`).join('');
 if(!b.length){$('msg').textContent='Todavía no hay presupuestos. Abre CaciqueFinanzas (puerto 5443), crea uno ("Start fresh") y vuelve aquí. · No budgets yet: create one in the budget app first.';return}
 load()}catch(e){if(e.message!=='login'){show(true);$('msg').textContent='No pude leer los presupuestos: '+e.message}}}
async function load(){$('msg').textContent='Leyendo… · Reading…';try{S=await j('/api/summary?budget='+encodeURIComponent($('bud').value));$('msg').textContent='';draw()}catch(e){if(e.message!=='login')$('msg').textContent='Error: '+e.message}}
function draw(){const s=S;$('cash').textContent=f(s.cash);$('net').textContent=f(s.avg_net);$('net').className='big '+(s.avg_net<0?'neg':'pos');
 $('ye').textContent=f(s.year_end);$('ye').className='big '+(s.year_end<0?'neg':'pos');
 $('alerts').innerHTML=s.alerts.length?s.alerts.map(a=>`<div class="alert ${a.level}">${a.text_es}<br><span class="sub">${a.text_en}</span></div>`).join(''):'<p class="sub">Todo dentro del plan este mes. 👏 · Everything within plan.</p>';
 $('rows').innerHTML=s.categories.filter(r=>r.spent||r.budgeted||r.max_times).map(r=>`<tr><td>${r.name}</td><td>${r.budgeted?f(r.budgeted):'—'}</td><td>${f(r.spent)}</td><td>${f(r.left)}</td><td>${r.times}</td>
  <td><input type="number" min="0" max="99" value="${r.max_times||''}" data-cat="${r.name.replace(/"/g,'&quot;')}" style="width:64px" aria-label="max times"></td><td><span class="pill ${r.status}">${{over:'Pasado',near:'Cerca',ok:'Bien',none:'',unplanned:'Sin plan'}[r.status]}</span></td></tr>`).join('');
 document.querySelectorAll('[data-cat]').forEach(i=>i.onchange=async()=>{await j('/api/rules',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({budget:S.budget,category:i.dataset.cat,max_times:parseInt(i.value)||0})});load()});
 scen()}
function scen(){const w=+$('save').value,s=S;$('saveL').textContent='$'+w;const extra=w*s.weeks_left,better=s.year_end+extra;
 $('saveTxt').innerHTML=`Con $${w} extra por semana terminas el año en <b class="${better<0?'neg':'pos'}">${f(better)}</b> en vez de ${f(s.year_end)}. · With $${w}/week more you end the year at <b>${f(better)}</b>.`;
 const W=600,H=180,L=56,R=10,T=12,B=26,n=Math.max(1,Math.ceil(s.months_left)),pts=[],pts2=[];
 for(let i=0;i<=n;i++){const m=Math.min(i,s.months_left);pts.push(s.cash+s.avg_net*m);pts2.push(s.cash+s.avg_net*m+w*m*4.348)}
 const all=pts.concat(pts2,[0]),lo=Math.min(...all),hi=Math.max(...all),rg=(hi-lo)||1,x=i=>L+(W-L-R)*i/n,y=v=>T+(H-T-B)*(1-(v-lo)/rg);
 const line=(p,c,d)=>`<polyline fill="none" stroke="${c}" stroke-width="3" ${d?'stroke-dasharray="6 5"':''} points="${p.map((v,i)=>x(i)+','+y(v)).join(' ')}"/>`;
 const now=new Date(s.today+'T12:00:00');let lab='';for(let i=0;i<=n;i++){const d=new Date(now.getFullYear(),now.getMonth()+i,1);lab+=`<text x="${x(i)}" y="${H-6}" text-anchor="middle">${i===0?'hoy':d.toLocaleString('es',{month:'short'})}</text>`}
 $('chart').innerHTML=`<line x1="${L}" x2="${W-R}" y1="${y(0)}" y2="${y(0)}" stroke="#2a3654"/><text x="${L-6}" y="${y(hi)+4}" text-anchor="end">${f(hi)}</text><text x="${L-6}" y="${y(lo)+4}" text-anchor="end">${f(lo)}</text>`+lab+line(pts,'#b6c3d5',true)+line(pts2,'#4cc38a',false)}
$('save').oninput=()=>S&&scen();$('bud').onchange=load;$('refresh').onclick=load;
async function coach(q){$('coach').textContent='…';try{const r=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({budget:$('bud').value,q})});
 if(r.status===401){show(false);return}const rd=r.body.getReader(),dec=new TextDecoder();let out='';$('coach').textContent='';
 for(;;){const {done,value}=await rd.read();if(done)break;out+=dec.decode(value,{stream:true});$('coach').textContent=out}}catch(e){$('coach').textContent='Error: '+e.message}}
$('report').onclick=()=>coach('Escríbeme el informe de este mes: qué va bien, qué categorías me pasé y qué cambio esta semana, y cómo terminaría el año si ahorro $'+$('save').value+' extra por semana.');
$('ask').onclick=()=>{if($('q').value.trim())coach($('q').value)};$('q').onkeydown=e=>{if(e.key==='Enter')$('ask').click()};
start();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def authed(self):
        c = self.headers.get("Cookie") or ""
        for part in c.split(";"):
            k, _, v = part.strip().partition("=")
            if k == "cf" and v:
                with LOCK:
                    exp = SESSIONS.get(v)
                return bool(exp and exp > time.time())
        return False

    def send(self, code, body, ctype="application/json", extra=None):
        data = body if isinstance(body, bytes) else (json.dumps(body) if ctype == "application/json" else body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if "charset" not in ctype else ""))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def body(self):
        try:
            return json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        except Exception:
            return {}

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/health":
            return self.send(200, b"ok", "text/plain")
        if u.path == "/":
            return self.send(200, PAGE, "text/html")
        if not self.authed():
            return self.send(401, {"error": "login"})
        try:
            if u.path == "/api/budgets":
                return self.send(200, budgets())
            if u.path == "/api/summary":
                bid = urllib.parse.parse_qs(u.query).get("budget", [""])[0]
                return self.send(200, summary(bid))
        except Exception as e:
            return self.send(502, {"error": "the budget helper did not answer (%s). Is CaciqueFinanzas running?" % e})
        self.send(404, {"error": "not found"})

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/login":
            pw = str(self.body().get("password", ""))
            if PASSWORD and hmac.compare_digest(pw.encode(), PASSWORD.encode()):
                tok = secrets.token_urlsafe(32)
                with LOCK:
                    SESSIONS[tok] = time.time() + 12 * 3600
                return self.send(200, {"ok": True}, extra={
                    "Set-Cookie": "cf=%s; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=43200" % tok})
            time.sleep(1.5)
            return self.send(403, {"error": "wrong password"})
        if not self.authed():
            return self.send(401, {"error": "login"})
        req = self.body()
        if u.path == "/api/rules":
            bid, cat = str(req.get("budget", "")), str(req.get("category", ""))[:80]
            n = int(req.get("max_times") or 0)
            rules = load_rules()
            mt = rules.setdefault(bid, {}).setdefault("max_times", {})
            if n > 0:
                mt[cat] = min(n, 99)
            else:
                mt.pop(cat, None)
            save_rules(rules)
            return self.send(200, {"ok": True})
        if u.path == "/api/ask":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()

            def chunk(text):
                b = text.encode()
                self.wfile.write(b"%x\r\n%s\r\n" % (len(b), b))
                self.wfile.flush()
            try:
                s = summary(str(req.get("budget", "")))
                if not ai_available():
                    chunk("La IA local (CaciqueGuía) no está prendida, así que te doy los números · The local AI is off, here are the numbers:\n\n"
                          + facts(s))
                else:
                    for piece in ask_ai(str(req.get("q", ""))[:1500], s):
                        chunk(piece)
            except Exception as e:
                chunk("\n(No pude preparar la respuesta · Could not answer: %s)" % e)
            try:
                self.wfile.write(b"0\r\n\r\n")
            except Exception:
                pass
            return
        self.send(404, {"error": "not found"})


def main():
    if not PASSWORD or not API_KEY:
        print("CaciqueFinanzas is not set up yet: bash ~/elcaciquedeck/finanzas/setup-finanzas.sh", file=sys.stderr)
        sys.exit(1)
    srv = ThreadingHTTPServer((BIND, PORT), Handler)
    print("CaciqueFinanzas coach on %s:%d" % (BIND, PORT), flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
