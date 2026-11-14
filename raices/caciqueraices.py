#!/usr/bin/env python3
"""
ElCaciqueDeck - Cacique Raíces: the family's own encyclopedia (our roots, our story).

  python3 ~/elcaciquedeck/raices/caciqueraices.py        (start-all.sh starts it; port 8098)

Each person of the family has a page that reads like an encyclopedia article: a box with the basics (born, studies,
work, spouse, children), the life story in sections (childhood, studies, work, love and family, achievements and
sacrifices, talents, faith and values, advice for the grandchildren), a photo gallery and a LIFE JOURNAL that keeps
growing year after year. Ancestors who already passed away get pages too, written by the family.

  http://<server>:8098/            the family: everyone's page, today in the family's history
  http://<server>:8098/p/<person>  one person's page          /linea  the family timeline
  http://<server>:8098/arbol       the generations             /libro  the whole family book (print / PDF)
  http://<server>:8098/admin       the adults' page: people, relations, PINs, family name, motto and crest

Privacy: everything stays in the house (Vault drive when it's there). Pages ask once per device for the FAMILY CODE,
so visitors on the Wi-Fi can't read them. Each person edits their own page with their own PIN (the admin can edit all).
Photos lose their hidden location data (GPS) when uploaded. Only the Python that comes with Ubuntu + python3-pil.
"""
import base64, datetime as dt, email.parser, email.policy, glob, hashlib, hmac, html, io, json, os, re, secrets
import sys, threading, time, urllib.parse, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("RAICES_PORT", "8098"))
BIND = os.environ.get("RAICES_BIND", "0.0.0.0")


def env_value(key, default=""):
    try:
        for line in open(os.path.join(HERE, ".env"), encoding="utf-8"):
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return default


DATA = os.environ.get("RAICES_DIR") or env_value("RAICES_DIR") or os.path.join(os.path.expanduser("~"), "elcaciquedeck-data", "raices")
ADMIN_PW = os.environ.get("RAICES_PASSWORD") or env_value("RAICES_PASSWORD")
SECRET = (os.environ.get("RAICES_SECRET") or env_value("RAICES_SECRET") or "dev-only-secret").encode()
LOCK = threading.Lock()
MAX_UPLOAD = 60 * 1024 * 1024

# ---------------------------------------------------------------- the questions (guided, for any age)
SECTIONS = [  # key, title es, title en, the questions that help write it (es), (en)
    ("infancia", "Infancia y raíces", "Childhood and roots",
     "¿Dónde creciste? ¿Cómo era tu casa, tu barrio, tu escuela? ¿Quiénes eran tus padres y abuelos? ¿Qué recuerdas con cariño?",
     "Where did you grow up? What were your home, neighborhood and school like? Who were your parents and grandparents?"),
    ("estudios", "Estudios", "Education",
     "¿Dónde estudiaste? ¿Qué títulos, premios o logros académicos tienes? ¿Qué maestro te marcó?",
     "Where did you study? What degrees, awards or achievements do you have? Which teacher marked you?"),
    ("trabajo", "Trabajo y oficio", "Work and craft",
     "¿En qué has trabajado? ¿Cómo empezaste? ¿De qué estás más orgulloso en tu trabajo?",
     "What work have you done? How did you start? What are you proudest of?"),
    ("familia", "Amor y familia", "Love and family",
     "¿Cómo conociste a tu pareja? ¿Dónde y cuándo se casaron? ¿Cómo llegaron los hijos? ¿Qué tradiciones tiene tu familia?",
     "How did you meet your partner? Where and when did you marry? How did the children arrive? What traditions does your family keep?"),
    ("logros", "Logros y sacrificios", "Achievements and sacrifices",
     "¿Qué es lo más difícil que has logrado? ¿Qué sacrificaste por tu familia? ¿Qué obstáculo venciste?",
     "What is the hardest thing you achieved? What did you sacrifice for your family? What obstacle did you overcome?"),
    ("talentos", "Talentos y gustos", "Talents and favorites",
     "¿Qué sabes hacer bien? ¿Qué te gusta: música, comida, lugares, pasatiempos? Todo talento cuenta.",
     "What are you good at? What do you love: music, food, places, hobbies? Every talent counts."),
    ("valores", "Fe y valores", "Faith and values",
     "¿En qué crees? ¿Qué valores te guiaron? ¿Qué te enseñaron tus padres que todavía usas?",
     "What do you believe in? Which values guided you? What did your parents teach you that you still use?"),
    ("consejos", "Para mis nietos", "For my grandchildren",
     "Si tus nietos leen esto dentro de 50 años, ¿qué quieres que sepan? ¿Qué consejo les das?",
     "If your grandchildren read this in 50 years, what do you want them to know? What advice do you give them?"),
]
BASICS = [  # key, es, en, placeholder
    ("nombre", "Nombre completo", "Full name", ""),
    ("apodo", "Cómo te dicen", "Nickname", "Ej.: Nana, Papi, Titi…"),
    ("rol", "En la familia es…", "In the family they are…", "Ej.: Abuela paterna · Paternal grandmother"),
    ("nacio_fecha", "Fecha de nacimiento", "Date of birth", "AAAA-MM-DD"),
    ("nacio_lugar", "Lugar de nacimiento", "Place of birth", "Ej.: Mayagüez, Puerto Rico"),
    ("partio_fecha", "Fecha en que partió (si ya no está)", "Date of passing (if no longer with us)", ""),
    ("estudios_corto", "Estudios (corto)", "Education (short)", "Ej.: Enfermería, UPR"),
    ("ocupacion", "Ocupación", "Occupation", "Ej.: Enfermera jefa"),
    ("conocido", "Conocido(a) por", "Known for", "Ej.: Su arroz con gandules y su paciencia"),
    ("frase", "Su frase", "Their saying", "Ej.: «Lo que se empieza, se termina.»"),
]
GENERATIONS = [(1, "Bisabuelos y antepasados · Ancestors"), (2, "Abuelos · Grandparents"), (3, "Padres y tíos · Parents"),
               (4, "Hijos y primos · Children"), (5, "Nietos · Grandchildren")]


# ---------------------------------------------------------------- storage (all inside the house)
def path(*p):
    return os.path.join(DATA, *p)


def load(name, default):
    try:
        with open(path(name), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save(name, value):
    os.makedirs(os.path.dirname(path(name)), exist_ok=True)
    tmp = path(name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path(name))


def family():
    f = {"nombre": "Nuestra familia", "lema": "", "escudo": "", "pedir_codigo": True, "codigo_hash": ""}
    f.update(load("familia.json", {}))
    return f


def people():
    out = {}
    for fn in glob.glob(path("personas", "*.json")):
        try:
            p = json.load(open(fn, encoding="utf-8"))
            if not p.get("borrado"):
                out[p["id"]] = p
        except Exception:
            pass
    return dict(sorted(out.items(), key=lambda kv: (kv[1].get("generacion", 3), kv[1].get("nacio_fecha") or "9999")))


def person(pid):
    if not re.fullmatch(r"[a-z0-9-]{1,40}", pid or ""):
        return None
    p = load(os.path.join("personas", pid + ".json"), None)
    return None if not p or p.get("borrado") else p


def save_person(p):
    p["actualizado"] = time.strftime("%Y-%m-%d %H:%M")
    save(os.path.join("personas", p["id"] + ".json"), p)


def slug(text):
    t = text.lower().strip()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ü", "u"), ("ñ", "n")):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40] or "persona"


def pin_hash(pin, salt=None):
    salt = salt or secrets.token_hex(8)
    return salt + "$" + hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), 200000).hex()


def pin_ok(pin, stored):
    if not stored or "$" not in stored or not pin:
        return False
    salt = stored.split("$", 1)[0]
    return hmac.compare_digest(pin_hash(pin, salt), stored)


# ---------------------------------------------------------------- photos: resized, rotated upright, GPS removed
def store_photo(raw, folder):
    """Save an uploaded photo (big + thumbnail). Returns the file name, or None if it isn't a picture."""
    try:
        from PIL import Image, ImageOps
        im = Image.open(io.BytesIO(raw))
        im = ImageOps.exif_transpose(im).convert("RGB")      # upright; the copy keeps NO hidden data (GPS, camera)
    except Exception:
        return None
    os.makedirs(path("fotos", folder), exist_ok=True)
    name = time.strftime("%Y%m%d-") + uuid.uuid4().hex[:8] + ".jpg"
    big = im.copy()
    big.thumbnail((1800, 1800))
    big.save(path("fotos", folder, name), "JPEG", quality=86)
    im.thumbnail((520, 520))
    im.save(path("fotos", folder, "t-" + name), "JPEG", quality=82)
    return folder + "/" + name


# ---------------------------------------------------------------- who may look / edit (signed cookies, no server memory)
def sign(value, days):
    exp = int(time.time()) + days * 86400
    msg = "%s|%d" % (value, exp)
    return base64.urlsafe_b64encode((msg + "|" + hmac.new(SECRET, msg.encode(), "sha256").hexdigest()).encode()).decode()


def unsign(token):
    try:
        value, exp, mac = base64.urlsafe_b64decode(token.encode()).decode().rsplit("|", 2)
        if hmac.compare_digest(mac, hmac.new(SECRET, ("%s|%s" % (value, exp)).encode(), "sha256").hexdigest()) and int(exp) > time.time():
            return value
    except Exception:
        pass
    return None


# ---------------------------------------------------------------- page pieces
def esc(s):
    return html.escape(str(s or ""), quote=True)


def paras(text):
    """Plain text from the family -> paragraphs (no HTML from users)."""
    parts = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    return "".join("<p>%s</p>" % esc(p).replace("\n", "<br>") for p in parts)


def age(p):
    try:
        b = dt.date.fromisoformat(p.get("nacio_fecha"))
        end = dt.date.fromisoformat(p["partio_fecha"]) if p.get("partio_fecha") else dt.date.today()
        return end.year - b.year - ((end.month, end.day) < (b.month, b.day))
    except Exception:
        return None


def nice_date(d):
    try:
        x = dt.date.fromisoformat(d)
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        return "%d de %s de %d · %s %d, %d" % (x.day, meses[x.month - 1], x.year, months[x.month - 1], x.day, x.year)
    except Exception:
        return esc(d)


def photo_url(f, thumb=False):
    if not f:
        return ""
    d, n = f.split("/", 1)
    return "/foto/%s/%s%s" % (esc(d), "t-" if thumb else "", esc(n))


def name_link(pid, ps):
    p = ps.get(pid)
    return '<a href="/p/%s">%s</a>' % (esc(pid), esc(p.get("apodo") or p.get("nombre"))) if p else ""


CSS = """
:root{--ink:#14303a;--sub:#4b6670;--line:#d9e6e3;--paper:#fffdf8;--glass:rgba(255,255,255,.78);--edge:rgba(255,255,255,.95);
 --aqua:#157989;--sun:#e2a443;--leaf:#2f8a5b;--serif:Georgia,"Times New Roman",serif}
*{box-sizing:border-box}html,body{margin:0}
body{font-family:"Segoe UI",Ubuntu,"Noto Sans",system-ui,sans-serif;color:var(--ink);min-height:100vh;
 background:radial-gradient(circle at 85% 0,rgba(255,236,170,.9),transparent 30%),linear-gradient(180deg,#e8f7f3,#cfeee2 55%,#a9dcc4);background-attachment:fixed}
a{color:var(--aqua)}
.top{max-width:1100px;margin:0 auto;padding:16px;display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:12px;text-decoration:none;color:var(--ink)}
.crest{width:52px;height:52px;border-radius:50%;object-fit:cover;background:linear-gradient(#ffe7a8,#e2a443);border:2px solid #fff;
 box-shadow:0 6px 16px rgba(120,90,20,.25);display:grid;place-items:center;font:700 22px var(--serif);color:#fff;flex:0 0 auto}
.brand b{display:block;font:700 22px var(--serif)}.brand small{display:block;color:var(--sub);font-size:13px}
nav{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
nav a,.btn,button{font:600 15px inherit;text-decoration:none;color:var(--ink);padding:9px 14px;border-radius:999px;cursor:pointer;
 background:linear-gradient(#fff,#e6f4f0);border:1px solid #bfdcd5;box-shadow:0 2px 6px rgba(20,90,80,.1);display:inline-block}
.btn.go,button.go{background:linear-gradient(#5fd38d,#1e8a4c);color:#fff;border-color:#1e8a4c}
button.no{background:linear-gradient(#f0857b,#b3392f);color:#fff;border-color:#b3392f}
.lang{display:inline-flex;gap:2px;padding:3px;border-radius:999px;background:var(--glass);border:1px solid var(--edge)}
.lang button{border:0;background:none;box-shadow:none;padding:6px 10px;font-size:13px}.lang button[aria-pressed=true]{background:#fff}
main{max-width:1100px;margin:0 auto;padding:0 16px 40px}
.panel{background:var(--glass);border:1px solid var(--edge);border-radius:26px;padding:24px;box-shadow:0 14px 38px rgba(24,102,98,.12);
 backdrop-filter:blur(14px)}
h1,h2,h3{font-family:var(--serif);font-weight:700;line-height:1.2}
.hero h1{font-size:clamp(28px,4vw,44px);margin:4px 0}.hero p{color:var(--sub);margin:0;font-size:17px}
.motto{font:italic 20px var(--serif);color:#8a6418;margin-top:8px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px;margin-top:16px}
.person{display:block;text-decoration:none;color:var(--ink);background:var(--paper);border:1px solid var(--line);border-radius:20px;overflow:hidden;
 box-shadow:0 6px 16px rgba(30,90,80,.1);transition:transform .15s}
.person:hover{transform:translateY(-2px)}
.person .ph{aspect-ratio:1;background:linear-gradient(135deg,#d8efe8,#f5e7c4);display:grid;place-items:center;font:700 54px var(--serif);color:#fff}
.person .ph img{width:100%;height:100%;object-fit:cover}
.person div.t{padding:12px 14px}.person b{display:block;font:700 18px var(--serif)}.person span{color:var(--sub);font-size:14px}
.gen{margin-top:26px}.gen h2{font-size:22px;margin:0 0 4px}
.today{border-left:5px solid var(--sun);background:rgba(255,248,225,.85);padding:12px 16px;border-radius:6px 16px 16px 6px;margin-top:16px}
/* the encyclopedia article */
.article{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:28px clamp(18px,4vw,40px);box-shadow:0 10px 30px rgba(30,90,80,.12)}
.article h1{font-size:clamp(30px,4.4vw,46px);margin:0;border-bottom:1px solid var(--line);padding-bottom:8px}
.from{color:var(--sub);font-size:14px;margin:6px 0 18px}
.info{float:right;width:min(320px,100%);margin:0 0 18px 24px;border:1px solid var(--line);border-radius:14px;background:#f7fbfa;overflow:hidden;font-size:15px}
.info img{width:100%;display:block}.info .cap{text-align:center;font:700 18px var(--serif);padding:10px}
.info table{width:100%;border-collapse:collapse}.info th,.info td{text-align:left;vertical-align:top;padding:7px 12px;border-top:1px solid var(--line)}
.info th{width:42%;color:var(--sub);font-weight:600}
.toc{display:inline-block;border:1px solid var(--line);border-radius:12px;background:#f7fbfa;padding:10px 18px;margin:4px 0 14px}
.toc b{display:block;margin-bottom:4px}.toc ol{margin:0;padding-left:20px}
nav.toc{display:inline-block}nav.toc a{background:none;border:0;box-shadow:none;padding:2px 0;border-radius:0;font-weight:400;color:var(--aqua);text-decoration:underline;display:inline}
.article h2{font-size:26px;border-bottom:1px solid var(--line);padding-bottom:4px;margin-top:28px}
.article p{font-size:17px;line-height:1.7;margin:0 0 12px}
.quote{font:italic 22px var(--serif);color:#8a6418;border-left:4px solid var(--sun);padding:6px 16px;margin:14px 0}
.empty{color:var(--sub);font-style:italic}
.gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
.gallery figure{margin:0}.gallery img{width:100%;aspect-ratio:1;object-fit:cover;border-radius:12px;display:block}
.gallery figcaption{font-size:13px;color:var(--sub);margin-top:4px}
.entry{border-left:3px solid var(--leaf);padding:4px 0 4px 16px;margin:14px 0}.entry time{color:var(--sub);font-size:14px}
.entry h3{margin:2px 0 6px;font-size:20px}
.clear{clear:both}
/* forms */
form.card{background:var(--paper);border:1px solid var(--line);border-radius:18px;padding:18px;margin:14px 0;display:flex;flex-direction:column;gap:10px}
label{display:flex;flex-direction:column;gap:5px;font-weight:600;font-size:15px}
label small{font-weight:400;color:var(--sub)}
input,textarea,select{font:inherit;font-size:17px;padding:11px 12px;border-radius:12px;border:1px solid #bfd6d1;background:#fff;color:var(--ink);width:100%}
textarea{min-height:120px;line-height:1.5}
.two{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.note{background:#fff;border-left:5px solid var(--leaf);padding:10px 14px;border-radius:10px;margin-bottom:12px}
.err{border-left-color:#b3392f}
.timeline .yr{font:700 24px var(--serif);margin:22px 0 4px;color:var(--aqua)}
@media(max-width:720px){.info{float:none;width:100%;margin:0 0 16px}.two{grid-template-columns:1fr}}
@media print{body{background:#fff}.top,nav,.noprint{display:none!important}.article{box-shadow:none;border:0;page-break-after:always}}
html[lang=en] .es,html[lang=es] .en{display:none}
"""

LANGJS = r"""<script>
(function(){var L;try{L=localStorage.getItem("cq-lang")}catch(e){}
 L=L||((navigator.language||"es").toLowerCase().indexOf("en")===0?"en":"es");var O=new WeakMap();
 function side(o){var k=o.indexOf(" · ");if(k<0)return o;var t=(L==="en"?o.slice(k+3):o.slice(0,k)).trim();
  if(/:\s*$/.test(o)&&!/:$/.test(t))t+=":";return o.match(/^\s*/)[0]+t+o.match(/\s*$/)[0];}
 function walk(n){if(n.nodeType===3){var o=O.has(n)?O.get(n):n.nodeValue;if(o.indexOf(" · ")<0)return;O.set(n,o);n.nodeValue=side(o);return;}
  if(n.nodeType!==1||/^(TEXTAREA|SCRIPT|STYLE)$/.test(n.nodeName)||n.hasAttribute("data-raw"))return;
  if(n.placeholder){var p=n.getAttribute("data-ph")||n.placeholder;n.setAttribute("data-ph",p);n.placeholder=side(p);}
  n.childNodes.forEach(walk);}
 function apply(){document.documentElement.lang=L;walk(document.body);
  document.querySelectorAll("[data-l]").forEach(function(b){b.setAttribute("aria-pressed",b.getAttribute("data-l")===L)});}
 document.addEventListener("click",function(e){var b=e.target.closest&&e.target.closest("[data-l]");if(!b)return;e.preventDefault();
  L=b.getAttribute("data-l");try{localStorage.setItem("cq-lang",L)}catch(x){}apply();});
 apply();})();
</script>"""


def page(title, body, fam=None, nav=True):
    fam = fam or family()
    crest = ('<img class="crest" src="%s" alt="">' % photo_url(fam["escudo"], True)) if fam.get("escudo") else \
        '<span class="crest" aria-hidden="true">%s</span>' % esc((fam["nombre"] or "F").replace("Familia ", "")[:1].upper())
    links = ('<nav><a href="/">Familia · Family</a><a href="/linea">Línea del tiempo · Timeline</a>'
             '<a href="/arbol">Generaciones · Generations</a><a href="/libro">El libro · The book</a>'
             '<div class="lang"><button type="button" data-l="es">ES</button><button type="button" data-l="en">EN</button></div></nav>') if nav else \
        '<nav><div class="lang"><button type="button" data-l="es">ES</button><button type="button" data-l="en">EN</button></div></nav>'
    return ("<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>%s</title><style>%s</style></head><body><header class=\"top\"><a class=\"brand\" href=\"/\">%s<span><b data-raw>%s</b>"
            "<small>Cacique Raíces · Our roots</small></span></a>%s</header><main>%s</main>%s</body></html>") % (
        esc(title), CSS, crest, esc(fam["nombre"]), links, body, LANGJS)


# ---------------------------------------------------------------- pages
def home_page():
    fam, ps = family(), people()
    today = dt.date.today()
    notes = []
    for p in ps.values():
        for key, what in (("nacio_fecha", "cumpleaños · birthday"), ("partio_fecha", "aniversario de su partida · remembrance")):
            try:
                d = dt.date.fromisoformat(p.get(key) or "")
                if (d.month, d.day) == (today.month, today.day):
                    notes.append('<div>%s: %s (%d)</div>' % (esc(what), name_link(p["id"], ps), d.year))
            except ValueError:
                pass
        for e in p.get("entradas", []):
            try:
                d = dt.date.fromisoformat(e.get("fecha") or "")
                if (d.month, d.day) == (today.month, today.day) and d.year < today.year:
                    notes.append('<div>Hace %d años · %d years ago: <a href="/p/%s#e-%s" data-raw>%s</a> (%s)</div>' % (
                        today.year - d.year, today.year - d.year, esc(p["id"]), esc(e["id"]), esc(e.get("titulo")), esc(p.get("apodo") or p["nombre"])))
            except ValueError:
                pass
    body = '<section class="panel hero"><h1 data-raw>%s</h1>%s<p>Nuestra historia, escrita por nosotros. · Our story, written by us.</p>%s</section>' % (
        esc(fam["nombre"]), '<div class="motto" data-raw>%s</div>' % esc(fam["lema"]) if fam.get("lema") else "",
        '<div class="today"><b>Hoy en la familia · Today in the family</b>%s</div>' % "".join(notes) if notes else "")
    if not ps:
        body += '<section class="panel" style="margin-top:16px"><p class="empty">Todavía no hay páginas. Un adulto las crea en /admin. · No pages yet. An adult creates them at /admin.</p></section>'
    for g, label in GENERATIONS:
        members = [p for p in ps.values() if p.get("generacion", 3) == g]
        if not members:
            continue
        cards = ""
        for p in members:
            ph = '<img src="%s" alt="" loading="lazy">' % photo_url(p.get("foto"), True) if p.get("foto") else esc((p.get("apodo") or p["nombre"])[:1])
            life = ""
            if p.get("nacio_fecha"):
                life = p["nacio_fecha"][:4] + (" – " + p["partio_fecha"][:4] if p.get("partio_fecha") else "")
            cards += '<a class="person" href="/p/%s"><div class="ph">%s</div><div class="t"><b data-raw>%s</b><span>%s</span><br><span>%s</span></div></a>' % (
                esc(p["id"]), ph, esc(p.get("apodo") or p["nombre"]), esc(p.get("rol")), esc(life))
        body += '<section class="gen"><h2>%s</h2><div class="grid">%s</div></section>' % (label, cards)
    return page(fam["nombre"], body, fam)


def person_page(p, can_edit):
    ps = people()
    rel = lambda key: ", ".join(filter(None, (name_link(x, ps) for x in p.get(key, []))))
    rows = []
    if p.get("nacio_fecha") or p.get("nacio_lugar"):
        a = age(p)
        rows.append(("Nacimiento · Born", "%s%s%s" % (nice_date(p.get("nacio_fecha")) if p.get("nacio_fecha") else "",
                                                      "<br>" + esc(p["nacio_lugar"]) if p.get("nacio_lugar") else "",
                                                      "" if a is None or p.get("partio_fecha") else " <span>(%d)</span>" % a)))
    if p.get("partio_fecha"):
        rows.append(("Partió · Passed", nice_date(p["partio_fecha"]) + ("" if age(p) is None else " <span>(%d)</span>" % age(p))))
    for key, label in (("estudios_corto", "Estudios · Education"), ("ocupacion", "Ocupación · Occupation"), ("conocido", "Conocido por · Known for")):
        if p.get(key):
            rows.append((label, '<span data-raw>%s</span>' % esc(p[key])))
    for key, label in (("pareja", "Pareja · Spouse"), ("padres", "Padres · Parents"), ("hijos", "Hijos · Children")):
        if rel(key):
            rows.append((label, rel(key)))
    info = '<aside class="info">%s<div class="cap" data-raw>%s</div><table>%s</table></aside>' % (
        '<img src="%s" alt="">' % photo_url(p.get("foto")) if p.get("foto") else "", esc(p["nombre"]),
        "".join("<tr><th>%s</th><td>%s</td></tr>" % r for r in rows))
    filled = [s for s in SECTIONS if (p.get("secciones") or {}).get(s[0], "").strip()]
    toc = '<nav class="toc" aria-label="Contenido"><b>Contenido · Contents</b><ol>%s%s%s</ol></nav>' % (
        "".join('<li><a href="#s-%s">%s · %s</a></li>' % (s[0], s[1], s[2]) for s in filled),
        '<li><a href="#galeria">Galería · Gallery</a></li>' if p.get("galeria") else "",
        '<li><a href="#diario">Diario de vida · Life journal</a></li>' if p.get("entradas") else "") if (filled or p.get("galeria") or p.get("entradas")) else ""
    lead = '<p><b data-raw>%s</b><span data-raw>%s</span>%s</p>' % (esc(p["nombre"]), (" (" + esc(p["apodo"]) + ")") if p.get("apodo") else "",
                                                                   (" — <span>%s</span>" % esc(p["rol"])) if p.get("rol") else "")
    body = '<article class="article">%s<h1 data-raw>%s</h1><div class="from">De la enciclopedia de la familia · From the family encyclopedia</div>%s%s%s' % (
        '<div class="noprint" style="float:right;margin-left:10px"><a class="btn" href="/p/%s/editar">✏️ Editar · Edit</a></div>' % esc(p["id"]) if can_edit is not None else "",
        esc(p["nombre"]), info, lead, '<div class="quote" data-raw>%s</div>' % esc(p["frase"]) if p.get("frase") else "")
    body += toc
    for key, es_t, en_t, _, _ in SECTIONS:
        txt = (p.get("secciones") or {}).get(key, "").strip()
        if txt:
            body += '<h2 id="s-%s">%s · %s</h2><div data-raw>%s</div>' % (key, es_t, en_t, paras(txt))
    if not filled:
        body += '<p class="empty">Esta historia todavía se está escribiendo. · This story is still being written.</p>'
    if p.get("galeria"):
        body += '<h2 id="galeria" class="clear">Galería · Gallery</h2><div class="gallery">%s</div>' % "".join(
            '<figure><a href="%s"><img src="%s" alt="" loading="lazy"></a><figcaption data-raw>%s</figcaption></figure>' % (
                photo_url(g["archivo"]), photo_url(g["archivo"], True), esc(g.get("pie"))) for g in p["galeria"])
    if p.get("entradas"):
        body += '<h2 id="diario" class="clear">Diario de vida · Life journal</h2>'
        for e in sorted(p["entradas"], key=lambda e: e.get("fecha") or "", reverse=True):
            body += '<div class="entry" id="e-%s"><time>%s</time><h3 data-raw>%s</h3><div data-raw>%s</div>%s</div>' % (
                esc(e["id"]), nice_date(e.get("fecha")), esc(e.get("titulo")), paras(e.get("texto")),
                '<div class="gallery">%s</div>' % "".join('<a href="%s"><img src="%s" alt="" loading="lazy"></a>' % (
                    photo_url(f), photo_url(f, True)) for f in e.get("fotos", [])) if e.get("fotos") else "")
    body += '<p class="from clear"><span>Última actualización · Last updated:</span> <span data-raw>%s</span></p></article>' % esc(p.get("actualizado", ""))
    return page(p["nombre"], body)


def edit_page(p, msg="", is_admin=False):
    sec = p.get("secciones") or {}
    basics = "".join('<label>%s · %s<input name="%s" value="%s" placeholder="%s" %s></label>' % (
        es, en, k, esc(p.get(k)), esc(ph), 'type="date"' if k.endswith("fecha") else "") for k, es, en, ph in BASICS)
    sections = "".join('<label>%s · %s<small>%s · %s</small><textarea name="s_%s">%s</textarea></label>' % (
        es_t, en_t, q_es, q_en, k, esc(sec.get(k))) for k, es_t, en_t, q_es, q_en in SECTIONS)
    note = '<div class="note">%s</div>' % esc(msg) if msg else ""
    today = dt.date.today().isoformat()
    body = """<section class="panel">%s<h1 data-raw>%s</h1><p>Escribe como si le contaras a tus nietos. No tiene que estar perfecto: se puede mejorar cuando quieras.
 · Write as if you were telling your grandchildren. It doesn't have to be perfect: you can improve it any time.</p>
<form class="card" method="post" action="/p/%s/editar" enctype="multipart/form-data">
<h2>1. Lo básico · The basics</h2>
<label>Foto principal · Main photo<small>Opcional · Optional</small><input type="file" name="foto" accept="image/*"></label>
<div class="two">%s</div>
<h2>2. Su historia · Their story</h2>%s
<div><button class="go">Guardar · Save</button> <a class="btn" href="/p/%s">Ver la página · View the page</a></div></form>

<form class="card" method="post" action="/p/%s/entrada" enctype="multipart/form-data">
<h2>3. Añadir al diario de vida · Add to the life journal</h2>
<p>Un momento, un logro, un viaje, una lección. Así la historia crece año tras año. · A moment, an achievement, a trip, a lesson.</p>
<div class="two"><label>Fecha · Date<input type="date" name="fecha" value="%s"></label><label>Título · Title<input name="titulo" required placeholder="Ej.: Nos casamos en San Germán"></label></div>
<label>Lo que pasó · What happened<textarea name="texto"></textarea></label>
<label>Fotos (hasta 6) · Photos (up to 6)<input type="file" name="fotos" accept="image/*" multiple></label>
<div><button class="go">Añadir · Add</button></div></form>

<form class="card" method="post" action="/p/%s/galeria" enctype="multipart/form-data">
<h2>4. Galería · Gallery</h2><p>Fotos de cuando era joven, la boda, la casa, los viajes. · Photos from youth, the wedding, the house, trips.</p>
<label>Fotos · Photos<input type="file" name="fotos" accept="image/*" multiple required></label>
<label>Pie de foto (para todas) · Caption (for all)<input name="pie" placeholder="Ej.: Boda, 1984"></label>
<div><button class="go">Subir · Upload</button></div></form>%s</section>""" % (
        note, esc(p["nombre"]), esc(p["id"]), basics, sections, esc(p["id"]), esc(p["id"]), today, esc(p["id"]),
        manage_items(p))
    return page("Editar · " + p["nombre"], body)


def manage_items(p):
    items = ""
    for e in sorted(p.get("entradas", []), key=lambda e: e.get("fecha") or "", reverse=True):
        items += '<li><span data-raw>%s – %s</span> <button name="entrada" value="%s" class="no">Quitar · Remove</button></li>' % (
            esc(e.get("fecha")), esc(e.get("titulo")), esc(e["id"]))
    for g in p.get("galeria", []):
        items += '<li><img src="%s" alt="" style="width:60px;height:60px;object-fit:cover;border-radius:8px;vertical-align:middle"> <span data-raw>%s</span> <button name="foto" value="%s" class="no">Quitar · Remove</button></li>' % (
            photo_url(g["archivo"], True), esc(g.get("pie")), esc(g["archivo"]))
    if not items:
        return ""
    return '<form class="card" method="post" action="/p/%s/quitar"><h2>5. Quitar · Remove</h2><ul style="list-style:none;padding:0;display:flex;flex-direction:column;gap:8px">%s</ul></form>' % (
        esc(p["id"]), items)


def timeline_page():
    ps = people()
    events = []
    for p in ps.values():
        who = '<a href="/p/%s" data-raw>%s</a>' % (esc(p["id"]), esc(p.get("apodo") or p["nombre"]))
        if p.get("nacio_fecha"):
            events.append((p["nacio_fecha"], "%s · %s" % ("Nace", "Born"), who, "", ""))
        if p.get("partio_fecha"):
            events.append((p["partio_fecha"], "Parte · Passes", who, "", ""))
        for e in p.get("entradas", []):
            events.append((e.get("fecha") or "", "", who, e.get("titulo"), "/p/%s#e-%s" % (p["id"], e["id"])))
    events.sort(key=lambda x: x[0])
    body, year = '<section class="panel timeline"><h1>Línea del tiempo · Timeline</h1>', None
    if not events:
        body += '<p class="empty">Todavía no hay fechas. · No dates yet.</p>'
    for d, kind, who, title, href in events:
        y = (d or "????")[:4]
        if y != year:
            body += '<div class="yr">%s</div>' % esc(y)
            year = y
        what = '<a href="%s" data-raw>%s</a>' % (esc(href), esc(title)) if title else '<span>%s</span>' % kind
        body += '<div class="entry"><time>%s</time><div>%s — %s</div></div>' % (nice_date(d), who, what)
    return page("Línea del tiempo", body + "</section>")


def tree_page():
    ps = people()
    body = '<section class="panel"><h1>Generaciones · Generations</h1><p>De los antepasados a los nietos. · From the ancestors to the grandchildren.</p>'
    for g, label in GENERATIONS:
        members = [p for p in ps.values() if p.get("generacion", 3) == g]
        if not members:
            continue
        body += '<h2>%s</h2><div class="grid">' % label
        for p in members:
            ph = '<img src="%s" alt="" loading="lazy">' % photo_url(p.get("foto"), True) if p.get("foto") else esc((p.get("apodo") or p["nombre"])[:1])
            sub = []
            if p.get("pareja"):
                sub.append("♥ " + ", ".join(esc((ps.get(x) or {}).get("apodo") or (ps.get(x) or {}).get("nombre") or "") for x in p["pareja"]))
            if p.get("hijos"):
                sub.append("↓ " + ", ".join(esc((ps.get(x) or {}).get("apodo") or (ps.get(x) or {}).get("nombre") or "") for x in p["hijos"]))
            body += '<a class="person" href="/p/%s"><div class="ph">%s</div><div class="t"><b data-raw>%s</b><span data-raw>%s</span></div></a>' % (
                esc(p["id"]), ph, esc(p.get("apodo") or p["nombre"]), "<br>".join(sub))
        body += "</div>"
    return page("Generaciones", body + "</section>")


def book_page():
    fam, ps = family(), people()
    body = '<section class="panel noprint" style="margin-bottom:16px"><p>Este es el libro completo de la familia. Para guardarlo en papel o PDF: menú del navegador → Imprimir. · The whole family book: browser menu → Print (paper or PDF).</p><button onclick="print()">🖨️ Imprimir · Print</button></section>'
    body += '<article class="article" style="text-align:center"><h1 data-raw>%s</h1>%s<p class="from">%s</p></article>' % (
        esc(fam["nombre"]), '<div class="quote" data-raw style="border:0">%s</div>' % esc(fam["lema"]) if fam.get("lema") else "", time.strftime("%Y"))
    for p in ps.values():
        inner = person_page(p, None)
        body += inner[inner.index("<article"):inner.index("</article>") + 10]
    return page("El libro · " + fam["nombre"], body, fam)


def code_page(err=""):
    fam = family()
    body = """<section class="panel" style="max-width:440px;margin:40px auto"><h1>Solo para la familia · Family only</h1>
<p>Escribe el código de la familia una vez en este equipo. · Type the family code once on this device.</p>%s
<form class="card" method="post" action="/entrar"><label>Código · Code<input name="codigo" type="password" inputmode="numeric" autofocus required></label>
<button class="go">Entrar · Enter</button></form></section>""" % ('<div class="note err">%s</div>' % esc(err) if err else "")
    return page(fam["nombre"], body, fam, nav=False)


def pin_page(p, err=""):
    body = """<section class="panel" style="max-width:440px;margin:40px auto"><h1 data-raw>%s</h1>
<p>Para editar, escribe tu PIN (o la contraseña del administrador). · To edit, type your PIN (or the admin password).</p>%s
<form class="card" method="post" action="/p/%s/pin"><label>PIN<input name="pin" type="password" autofocus required></label>
<button class="go">Entrar · Enter</button></form></section>""" % (esc(p["nombre"]), '<div class="note err">%s</div>' % esc(err) if err else "", esc(p["id"]))
    return page("PIN", body)


def admin_page(msg=""):
    fam, ps = family(), people()
    opts = lambda sel: "".join('<option value="%s"%s>%s</option>' % (esc(i), " selected" if i in sel else "", esc(x.get("apodo") or x["nombre"])) for i, x in ps.items())
    gens = lambda sel: "".join('<option value="%d"%s>%s</option>' % (g, " selected" if g == sel else "", label) for g, label in GENERATIONS)
    rows = ""
    for pid, p in ps.items():
        rows += """<form class="card" method="post" action="/admin/persona"><input type="hidden" name="id" value="%s">
<h3 data-raw>%s <small>(%s)</small> %s</h3>
<div class="two"><label>Generación · Generation<select name="generacion">%s</select></label>
<label>PIN nuevo (4+ números) · New PIN<input name="pin" inputmode="numeric" placeholder="%s"></label></div>
<div class="two"><label>Pareja · Spouse<select name="pareja" multiple size="3">%s</select></label>
<label>Padres · Parents<select name="padres" multiple size="3">%s</select></label></div>
<label>Hijos · Children<select name="hijos" multiple size="3">%s</select></label>
<div><button class="go">Guardar · Save</button> <a class="btn" href="/p/%s/editar">Escribir su página · Write their page</a>
<button name="borrar" value="1" class="no" formnovalidate>Quitar · Remove</button></div></form>""" % (
            esc(pid), esc(p["nombre"]), esc(pid), "🕊️" if p.get("partio_fecha") else "", gens(p.get("generacion", 3)),
            "tiene PIN · has a PIN" if p.get("pin") else "sin PIN · no PIN", opts(p.get("pareja", [])), opts(p.get("padres", [])),
            opts(p.get("hijos", [])), esc(pid))
    body = """<section class="panel"><h1>Administrar · Manage</h1>%s
<form class="card" method="post" action="/admin/familia" enctype="multipart/form-data"><h2>La familia · The family</h2>
<div class="two"><label>Nombre de la familia · Family name<input name="nombre" value="%s"></label><label>Lema · Motto<input name="lema" value="%s"></label></div>
<label>Escudo o emblema (imagen) · Crest (image)<input type="file" name="escudo" accept="image/*"></label>
<div class="two"><label>Código para ver las páginas · Family code to view<input name="codigo" inputmode="numeric" placeholder="%s"></label>
<label style="flex-direction:row;align-items:center;gap:8px;margin-top:26px"><input type="checkbox" name="pedir_codigo" value="1" style="width:auto"%s> Pedir el código (recomendado: visitas en el Wi-Fi) · Ask for the code</label></div>
<div><button class="go">Guardar · Save</button></div></form>
<form class="card" method="post" action="/admin/nueva"><h2>Añadir persona · Add a person</h2>
<div class="two"><label>Nombre completo · Full name<input name="nombre" required></label><label>En la familia es… · Role<input name="rol" placeholder="Abuela paterna · Paternal grandmother"></label></div>
<div class="two"><label>Generación · Generation<select name="generacion">%s</select></label><label>PIN para editar · Edit PIN<input name="pin" inputmode="numeric" placeholder="1234"></label></div>
<div><button class="go">Añadir · Add</button></div></form>
<h2>Personas · People</h2>%s
<p><a class="btn" href="/admin/exportar">⬇️ Copia de todo el texto (JSON) · Export all text</a> <a class="btn" href="/admin/salir">Salir · Log out</a></p></section>""" % (
        '<div class="note">%s</div>' % esc(msg) if msg else "", esc(fam["nombre"]), esc(fam["lema"]),
        "hay un código · a code is set" if fam.get("codigo_hash") else "ej.: 1925", " checked" if fam.get("pedir_codigo") else "",
        gens(3), rows or '<p class="empty">Nadie todavía. · Nobody yet.</p>')
    return page("Administrar", body, fam)


def admin_login(err=""):
    body = """<section class="panel" style="max-width:440px;margin:40px auto"><h1>Administrar · Manage</h1>%s
<form class="card" method="post" action="/admin/entrar"><label>Contraseña · Password<input name="pw" type="password" autofocus required></label>
<button class="go">Entrar · Log in</button></form></section>""" % ('<div class="note err">%s</div>' % esc(err) if err else "")
    return page("Administrar", body, nav=False)


# ---------------------------------------------------------------- web server
def parse_form(handler):
    n = int(handler.headers.get("Content-Length") or 0)
    if n > MAX_UPLOAD:
        raise ValueError("too big")
    raw = handler.rfile.read(n)
    ctype = handler.headers.get("Content-Type", "")
    fields, files = {}, {}
    if ctype.startswith("multipart/form-data"):
        msg = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(
            b"Content-Type: " + ctype.encode() + b"\r\nMIME-Version: 1.0\r\n\r\n" + raw)
        for part in msg.iter_parts():
            name = part.get_param("name", header="content-disposition")
            if not name:
                continue
            data = part.get_payload(decode=True) or b""
            if part.get_filename() is not None:
                if data:
                    files.setdefault(name, []).append(data)
            else:
                fields.setdefault(name, []).append(data.decode("utf-8", "replace"))
    else:
        for k, v in urllib.parse.parse_qs(raw.decode("utf-8", "replace"), keep_blank_values=True).items():
            fields[k] = v
    return {k: v[0] for k, v in fields.items()}, fields, files


class Handler(BaseHTTPRequestHandler):
    server_version = "CaciqueRaices"

    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="text/html; charset=utf-8", headers=None):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        if ctype.startswith("text/html"):
            self.send_header("Cache-Control", "no-store")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def go(self, where, cookie=None):
        h = {"Location": where}
        if cookie:
            h["Set-Cookie"] = cookie
        self.send(303, "", headers=h)

    def cookie(self, name):
        for part in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == name:
                return v
        return ""

    def can_view(self):
        fam = family()
        return (not (fam.get("pedir_codigo") and fam.get("codigo_hash")) or unsign(self.cookie("rv")) == "familia"
                or bool(self.editor()))             # the admin and anyone editing are family

    def editor(self):
        return unsign(self.cookie("re"))           # "admin" or a person's id

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        parts = [x for x in u.path.split("/") if x]
        q = dict(urllib.parse.parse_qsl(u.query))
        try:
            if u.path == "/health":
                return self.send(200, "ok", "text/plain")
            if u.path == "/admin":
                if not ADMIN_PW:
                    return self.send(503, "Run raices/setup-raices.sh first.", "text/plain")
                return self.send(200, admin_page(q.get("m", "")) if self.editor() == "admin" else admin_login())
            if u.path == "/admin/salir":
                return self.go("/", "re=; Path=/; Max-Age=0")
            if u.path == "/admin/exportar" and self.editor() == "admin":
                data = json.dumps({"familia": {k: v for k, v in family().items() if k != "codigo_hash"},
                                   "personas": [{k: v for k, v in p.items() if k != "pin"} for p in people().values()]},
                                  ensure_ascii=False, indent=1)
                return self.send(200, data, "application/json; charset=utf-8",
                                 {"Content-Disposition": 'attachment; filename="raices-%s.json"' % time.strftime("%Y-%m-%d")})
            if not self.can_view():
                return self.send(200, code_page())
            if u.path == "/":
                return self.send(200, home_page())
            if u.path == "/linea":
                return self.send(200, timeline_page())
            if u.path == "/arbol":
                return self.send(200, tree_page())
            if u.path == "/libro":
                return self.send(200, book_page())
            if len(parts) == 3 and parts[0] == "foto" and re.fullmatch(r"[a-z0-9-]{1,40}", parts[1]) and re.fullmatch(r"(t-)?[\w-]+\.jpg", parts[2]):
                f = path("fotos", parts[1], parts[2])
                if os.path.isfile(f):
                    return self.send(200, open(f, "rb").read(), "image/jpeg", {"Cache-Control": "private, max-age=86400"})
                return self.send(404, "not found", "text/plain")
            if len(parts) >= 2 and parts[0] == "p":
                p = person(parts[1])
                if not p:
                    return self.send(404, page("No encontrado", '<section class="panel"><h1>No encontrado · Not found</h1></section>'))
                ed = self.editor()
                if len(parts) == 2:
                    return self.send(200, person_page(p, ed in ("admin", p["id"])))
                if parts[2] == "editar":
                    if ed not in ("admin", p["id"]):
                        return self.send(200, pin_page(p))
                    return self.send(200, edit_page(p, q.get("m", ""), ed == "admin"))
            return self.send(404, page("No encontrado", '<section class="panel"><h1>No encontrado · Not found</h1></section>'))
        except Exception as e:
            print("  ! GET %s: %s" % (u.path, e), file=sys.stderr, flush=True)
            return self.send(500, "error", "text/plain")

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        parts = [x for x in u.path.split("/") if x]
        try:
            if (self.headers.get("Origin") or "").split("://")[-1] not in ("", self.headers.get("Host", "")):
                return self.send(403, "forbidden", "text/plain")
            f, multi, files = parse_form(self)
            if u.path == "/entrar":
                time.sleep(0.6)
                fam = family()
                if pin_ok(f.get("codigo", ""), fam.get("codigo_hash")):
                    return self.go("/", "rv=%s; Path=/; HttpOnly; SameSite=Lax; Max-Age=%d" % (sign("familia", 365), 365 * 86400))
                return self.send(200, code_page("Código incorrecto · Wrong code"))
            if u.path == "/admin/entrar":
                time.sleep(0.6)
                if ADMIN_PW and hmac.compare_digest(f.get("pw", "").encode(), ADMIN_PW.encode()):
                    return self.go("/admin", "re=%s; Path=/; HttpOnly; SameSite=Strict; Max-Age=43200" % sign("admin", 1))
                return self.send(200, admin_login("Contraseña incorrecta · Wrong password"))
            if parts[:1] == ["admin"]:
                if self.editor() != "admin":
                    return self.go("/admin")
                return self.admin_post(u.path, f, multi, files)
            if len(parts) == 3 and parts[0] == "p":
                p = person(parts[1])
                if not p:
                    return self.send(404, "not found", "text/plain")
                if parts[2] == "pin":
                    time.sleep(0.6)
                    pin = f.get("pin", "")
                    if pin_ok(pin, p.get("pin")):
                        who = p["id"]
                    elif ADMIN_PW and hmac.compare_digest(pin.encode(), ADMIN_PW.encode()):
                        who = "admin"
                    else:
                        return self.send(200, pin_page(p, "PIN incorrecto · Wrong PIN"))
                    return self.go("/p/%s/editar" % p["id"], "re=%s; Path=/; HttpOnly; SameSite=Strict; Max-Age=43200" % sign(who, 1))
                if self.editor() not in ("admin", p["id"]):
                    return self.go("/p/%s/editar" % p["id"])
                return self.person_post(p, parts[2], f, multi, files)
            return self.send(404, "not found", "text/plain")
        except ValueError:
            return self.send(413, page("Muy grande", '<section class="panel"><h1>Demasiado grande · Too big</h1><p>Sube menos fotos a la vez. · Upload fewer photos at once.</p></section>'))
        except Exception as e:
            print("  ! POST %s: %s" % (u.path, e), file=sys.stderr, flush=True)
            return self.send(500, "error", "text/plain")

    def person_post(self, p, action, f, multi, files):
        with LOCK:
            p = person(p["id"])
            note = "Guardado · Saved"
            if action == "editar":
                for k, _, _, _ in BASICS:
                    if k in f:
                        p[k] = f[k].strip()[:300]
                if not p.get("nombre"):
                    p["nombre"] = p["id"]
                p["secciones"] = {k: f.get("s_" + k, "").strip()[:20000] for k, *_ in SECTIONS}
                if files.get("foto"):
                    got = store_photo(files["foto"][0], p["id"])
                    if got:
                        p["foto"] = got
                    else:
                        note = "La foto no se pudo leer · The photo could not be read"
            elif action == "entrada":
                fotos = [x for x in (store_photo(r, p["id"]) for r in files.get("fotos", [])[:6]) if x]
                if f.get("titulo", "").strip():
                    p.setdefault("entradas", []).append({"id": uuid.uuid4().hex[:8], "fecha": f.get("fecha", "")[:10],
                                                         "titulo": f["titulo"].strip()[:200], "texto": f.get("texto", "").strip()[:20000],
                                                         "fotos": fotos, "creado": time.strftime("%Y-%m-%d %H:%M")})
                    note = "Añadido al diario · Added to the journal"
            elif action == "galeria":
                n = 0
                for r in files.get("fotos", [])[:20]:
                    got = store_photo(r, p["id"])
                    if got:
                        p.setdefault("galeria", []).append({"archivo": got, "pie": f.get("pie", "").strip()[:200]})
                        n += 1
                note = "%d fotos subidas · photos uploaded" % n
            elif action == "quitar":
                if f.get("entrada"):
                    p["entradas"] = [e for e in p.get("entradas", []) if e["id"] != f["entrada"]]
                if f.get("foto"):
                    p["galeria"] = [g for g in p.get("galeria", []) if g["archivo"] != f["foto"]]
                note = "Quitado · Removed"
            else:
                return self.send(404, "not found", "text/plain")
            save_person(p)
        return self.go("/p/%s/editar?m=%s" % (p["id"], urllib.parse.quote(note)))

    def admin_post(self, upath, f, multi, files):
        with LOCK:
            if upath == "/admin/familia":
                fam = load("familia.json", {})
                fam["nombre"] = f.get("nombre", "").strip()[:80] or "Nuestra familia"
                fam["lema"] = f.get("lema", "").strip()[:160]
                fam["pedir_codigo"] = f.get("pedir_codigo") == "1"
                if f.get("codigo", "").strip():
                    fam["codigo_hash"] = pin_hash(f["codigo"].strip())
                if files.get("escudo"):
                    got = store_photo(files["escudo"][0], "familia")
                    if got:
                        fam["escudo"] = got
                save("familia.json", fam)
                return self.go("/admin?m=" + urllib.parse.quote("Guardado · Saved"))
            if upath == "/admin/nueva":
                name = f.get("nombre", "").strip()[:120]
                if not name:
                    return self.go("/admin")
                pid, n = slug(name), 2
                while person(pid):
                    pid, n = "%s-%d" % (slug(name), n), n + 1
                p = {"id": pid, "nombre": name, "rol": f.get("rol", "").strip()[:120], "generacion": int(f.get("generacion") or 3),
                     "secciones": {}, "entradas": [], "galeria": []}
                if len(f.get("pin", "").strip()) >= 4:
                    p["pin"] = pin_hash(f["pin"].strip())
                save_person(p)
                return self.go("/admin?m=" + urllib.parse.quote("Añadido · Added: " + name))
            if upath == "/admin/persona":
                p = person(f.get("id", ""))
                if not p:
                    return self.go("/admin")
                if f.get("borrar"):
                    p["borrado"] = True                   # kept on disk (nothing is erased), hidden from the pages
                    save_person(p)
                    return self.go("/admin?m=" + urllib.parse.quote("Quitado (guardado en el disco) · Removed (kept on disk)"))
                ps = people()
                p["generacion"] = int(f.get("generacion") or 3)
                for key in ("pareja", "padres", "hijos"):
                    p[key] = [x for x in multi.get(key, []) if x in ps and x != p["id"]]
                if len(f.get("pin", "").strip()) >= 4:
                    p["pin"] = pin_hash(f["pin"].strip())
                save_person(p)
                # keep both sides of a relation in step (spouse <-> spouse, parent <-> child)
                for other in ps.values():
                    if other["id"] == p["id"]:
                        continue
                    changed = False
                    for mine, theirs in (("pareja", "pareja"), ("padres", "hijos"), ("hijos", "padres")):
                        want = other["id"] in p.get(mine, [])
                        have = p["id"] in other.get(theirs, [])
                        if want and not have:
                            other.setdefault(theirs, []).append(p["id"]); changed = True
                        elif have and not want:
                            other[theirs] = [x for x in other.get(theirs, []) if x != p["id"]]; changed = True
                    if changed:
                        save_person(other)
                return self.go("/admin?m=" + urllib.parse.quote("Guardado · Saved"))
        return self.send(404, "not found", "text/plain")


def main():
    os.makedirs(path("personas"), exist_ok=True)
    os.makedirs(path("fotos"), exist_ok=True)
    try:
        os.chmod(DATA, 0o700)
    except OSError:
        pass
    srv = ThreadingHTTPServer((BIND, PORT), Handler)
    print("  Cacique Raíces on port %d (data: %s)" % (PORT, DATA), flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
