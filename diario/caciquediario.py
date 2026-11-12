#!/usr/bin/env python3
"""
ElCaciqueDeck - Cacique Diario: the home's message of the day (faith, family, order, health, knowledge, courage).

  python3 ~/elcaciquedeck/diario/caciquediario.py            (start-all.sh starts it; port 8097)
  python3 ~/elcaciquedeck/diario/caciquediario.py --hoy      make today's messages + pictures now
  python3 ~/elcaciquedeck/diario/caciquediario.py --probar   only SHOW today's picks (saves nothing)

Open (any device at home):
  http://<server>:8097/                     shared screen (TV, kitchen, tablet): family messages, both languages
  http://<server>:8097/?para=<person>       one person's screen (adds the messages for their roles)
  http://<server>:8097/?modo=espejo         smart mirror: black background, white text
  http://<server>:8097/admin                the adults' page: approve, people, reminders, own messages (password)
  http://<server>:8097/api/hoy?para=...     JSON for the mirror, CaciqueHome and other screens

Every night (04:00) it:
  1. picks each person's messages for the day (no repeats for 30 days, different themes),
  2. draws 2-3 picture cards with the family messages (for the photo frames and the TV screensaver),
  3. puts them in the "Cacique Diario" album in CaciquePhotos (Immich), and takes out the ones older than 7 days,
  4. optionally asks the local AI (CaciqueGuía) for new messages, which wait in the approval page.
Nothing is shown before an adult approves it if it is a Bible verse or AI-written. Nothing leaves the house.
Only the Python that comes with Ubuntu is needed (+ python3-pil for the picture cards).
"""
import datetime as dt
import glob, hmac, html, io, json, os, random, re, secrets, sys, threading, time, uuid
import urllib.error, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LIB_DIR = os.path.join(HERE, "biblioteca")
DATA = os.environ.get("DIARIO_DATA") or os.path.join(os.path.expanduser("~"), "elcaciquedeck-data", "diario")
PORT = int(os.environ.get("DIARIO_PORT", "8097"))
BIND = os.environ.get("DIARIO_BIND", "0.0.0.0")
OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
ALBUM = "Cacique Diario"
NO_REPEAT_DAYS = 30
SESSIONS, LOCK, DAY_LOCK = {}, threading.Lock(), threading.Lock()

TEMAS = {   # key: (es, en)
    "fe": ("Fe", "Faith"), "familia": ("Familia", "Family"), "orden": ("Orden", "Order"),
    "salud": ("Salud", "Health"), "saber": ("Saber y riqueza", "Knowledge & wealth"),
    "animo": ("Ánimo", "Encouragement"), "casa": ("La casa", "Home"),
}
ROLES = {   # key: (es, en)
    "adultos": ("Adulto", "Adult"), "esposo": ("Esposo", "Husband"), "esposa": ("Esposa", "Wife"),
    "padres": ("Padre o madre", "Parent"), "abuelos": ("Abuelo o abuela", "Grandparent"), "hijos": ("Hijo o hija", "Child"),
}
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def env_value(path, key, default=""):
    try:
        for line in open(path, encoding="utf-8"):
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return default


ENV = os.path.join(HERE, ".env")
PASSWORD = os.environ.get("DIARIO_PASSWORD") or env_value(ENV, "DIARIO_PASSWORD")
MODEL = os.environ.get("GUIDE_MODEL") or env_value(os.path.join(REPO, "guide", ".env"), "GUIDE_MODEL", "qwen2.5:3b")


# ================================================================ small file helpers (all data lives in DATA)
def path(*p):
    return os.path.join(DATA, *p)


def load(name, default):
    try:
        with open(path(name), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save(name, value):
    os.makedirs(DATA, exist_ok=True)
    tmp = path(name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path(name))
    if name == "ajustes.json":
        os.chmod(path(name), 0o600)   # holds the CaciquePhotos key


DEFAULT_SETTINGS = {"por_dia": 3, "hora": 4, "guardar_dias": 7, "immich_url": "http://127.0.0.1:2283",
                    "immich_key": "", "albumes_extra": "", "ia": True, "fondos": "", "presencia": True}


def settings():
    s = dict(DEFAULT_SETTINGS)
    s.update(load("ajustes.json", {}))
    return s


def people():
    p = load("personas.json", {})
    if "familia" not in p:
        p["familia"] = {"nombre": "Familia", "roles": [], "temas": list(TEMAS), "idioma": "es"}
    return p


def slug(text):
    t = text.lower().strip()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ü", "u"), ("ñ", "n")):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:30]


# ================================================================ the message library
def library():
    """Every message: the library in GitHub + the family's own (approved) messages."""
    items = []
    for f in sorted(glob.glob(os.path.join(LIB_DIR, "*.json"))):
        try:
            items += json.load(open(f, encoding="utf-8"))
        except Exception as e:
            print("  ! could not read", f, e, file=sys.stderr)
    items += load("propios.json", [])
    return items


def status_of(item, decisions=None):
    """'ok' (can be shown), 'pendiente' (waits for an adult) or 'no' (rejected)."""
    d = (decisions if decisions is not None else load("decisiones.json", {})).get(item["id"])
    if d in ("ok", "no"):
        return d
    return "pendiente" if item.get("verificar") else "ok"


def usable():
    dec, edits = load("decisiones.json", {}), load("ediciones.json", {})
    out = []
    for it in library():
        if status_of(it, dec) == "ok":
            e = edits.get(it["id"])
            out.append(dict(it, **e) if e else it)
    return out


def fits(item, person):
    para = item.get("para", "todos")
    para = para if isinstance(para, list) else [para]
    return item.get("tema") in person.get("temas", TEMAS) and ("todos" in para or any(r in person.get("roles", []) for r in para))


def reminders_for(day, person):
    out = []
    for i, r in enumerate(load("recordatorios.json", [])):
        if day.weekday() in r.get("dias", []) and r.get("activo", True):
            para = r.get("para", "todos")
            if para == "todos" or para in person.get("roles", []) or para == person.get("_id"):
                out.append({"id": "rec-%d" % i, "tema": "casa", "es": r["es"], "en": r.get("en", ""),
                            "fuente": "Recordatorio · Reminder", "recordatorio": True})
    return out


def pick(person_id, day, write=True):
    """Today's messages for one person. Same answer all day (saved), different themes, no repeats for 30 days."""
    key = day.isoformat()
    cache = load(os.path.join("dias", key + ".json"), {})
    if person_id in cache:
        return cache[person_id]
    ps = people()
    person = dict(ps.get(person_id) or ps["familia"], _id=person_id)
    n = int(person.get("por_dia") or settings()["por_dia"])
    history = load("historial.json", {})
    seen = history.get(person_id, {})
    # shown in the last 30 days (today's own picks don't count, so redoing today gives the same messages)
    recent = {i for i, d in seen.items() if 0 < (day - dt.date.fromisoformat(d)).days < NO_REPEAT_DAYS}
    pool = [it for it in usable() if fits(it, person)]
    fresh = [it for it in pool if it["id"] not in recent] or pool
    rng = random.Random("%s|%s" % (key, person_id))
    rng.shuffle(fresh)
    chosen, themes = [], set()
    for it in fresh:                       # first pass: one per theme
        if len(chosen) >= n:
            break
        if it["tema"] not in themes:
            chosen.append(it); themes.add(it["tema"])
    for it in fresh:                       # then fill up
        if len(chosen) >= n:
            break
        if it not in chosen:
            chosen.append(it)
    msgs = [{k: it.get(k, "") for k in ("id", "tema", "es", "en", "fuente")} for it in chosen]
    msgs = reminders_for(day, person) + msgs
    if write:
        for m in msgs:
            if not m.get("recordatorio"):
                seen[m["id"]] = key
        history[person_id] = seen
        save("historial.json", history)
        cache[person_id] = msgs
        os.makedirs(path("dias"), exist_ok=True)
        save(os.path.join("dias", key + ".json"), cache)
    return msgs


# ================================================================ picture cards (photo frames, TV screensaver)
FONT_DIRS = ["/usr/share/fonts/truetype/ubuntu", "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype",
             "/usr/share/fonts"]


def font(kind, size):
    from PIL import ImageFont
    names = {"bold": ["Ubuntu-B.ttf", "Ubuntu[wdth,wght].ttf", "DejaVuSans-Bold.ttf"],
             "italic": ["Ubuntu-RI.ttf", "Ubuntu-Italic[wdth,wght].ttf", "DejaVuSans-Oblique.ttf"],
             "regular": ["Ubuntu-R.ttf", "Ubuntu[wdth,wght].ttf", "DejaVuSans.ttf"]}[kind]
    for d in FONT_DIRS:
        for n in names:
            for f in glob.glob(os.path.join(d, "**", n), recursive=True):
                try:
                    return ImageFont.truetype(f, size)
                except Exception:
                    pass
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def wrap(draw, text, fnt, width):
    lines, line = [], ""
    for word in text.split():
        test = (line + " " + word).strip()
        if draw.textlength(test, font=fnt) <= width or not line:
            line = test
        else:
            lines.append(line); line = word
    if line:
        lines.append(line)
    return lines


SKIES = [  # (top, middle, bottom) - Aero nature: sky, sea, leaves, sunrise
    ((52, 140, 220), (110, 200, 235), (120, 200, 120)),
    ((26, 90, 170), (60, 170, 200), (40, 150, 130)),
    ((250, 170, 110), (240, 210, 160), (110, 180, 200)),
    ((40, 120, 90), (110, 190, 120), (200, 230, 150)),
    ((70, 90, 190), (130, 170, 230), (230, 200, 230)),
]


def background(W, H, rng, photos):
    from PIL import Image, ImageDraw, ImageFilter
    if photos:
        try:
            im = Image.open(rng.choice(photos)).convert("RGB")
            s = max(W / im.width, H / im.height)
            im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1))
            x, y = (im.width - W) // 2, (im.height - H) // 2
            return im.crop((x, y, x + W, y + H)).filter(ImageFilter.GaussianBlur(2))
        except Exception:
            pass
    top, mid, bot = rng.choice(SKIES)
    im = Image.new("RGB", (W, H))
    px = ImageDraw.Draw(im)
    for yy in range(H):
        t = yy / (H - 1)
        a, b, u = (top, mid, t * 2) if t < .5 else (mid, bot, (t - .5) * 2)
        px.line([(0, yy), (W, yy)], fill=tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(3)))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    for _ in range(18):                        # soft glossy bubbles
        r = rng.randint(H // 30, H // 7)
        x, y = rng.randint(0, W), rng.randint(0, H)
        g.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, rng.randint(18, 45)))
    g.ellipse([-W // 4, int(H * .78), W + W // 4, int(H * 1.6)], fill=(255, 255, 255, 40))   # gentle hill light
    glow = glow.filter(ImageFilter.GaussianBlur(H // 60))
    return Image.alpha_composite(im.convert("RGBA"), glow).convert("RGB")


def card(msg, out_file, rng, photos, W=1920, H=1080):
    from PIL import Image, ImageDraw, ImageFilter
    im = background(W, H, rng, photos).convert("RGBA")
    pane = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(pane)
    pad_x = int(W * .12)
    box = [pad_x - 60, int(H * .16), W - pad_x + 60, int(H * .84)]
    d.rounded_rectangle(box, radius=48, fill=(255, 255, 255, 70), outline=(255, 255, 255, 150), width=3)
    d.rounded_rectangle([box[0] + 4, box[1] + 4, box[2] - 4, box[1] + (box[3] - box[1]) // 3], radius=44, fill=(255, 255, 255, 38))
    im = Image.alpha_composite(im, pane)
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    width = W - 2 * pad_x
    es, en, src = msg.get("es", ""), msg.get("en", ""), msg.get("fuente", "")
    size = 74 if len(es) < 70 else 62 if len(es) < 120 else 52
    f_es, f_en, f_src = font("bold", size), font("italic", int(size * .55)), font("regular", 30)
    l_es = wrap(draw, es, f_es, width)
    l_en = wrap(draw, en, f_en, width) if en else []
    h_es, h_en = size * 1.22, size * .55 * 1.3
    total = len(l_es) * h_es + (30 + len(l_en) * h_en if l_en else 0) + (60 if src else 0)
    y = (H - total) / 2
    lines = []                             # (text, font, color, y)
    for ln in l_es:
        lines.append((ln, f_es, (255, 255, 255), y)); y += h_es
    if l_en:
        y += 30
        for ln in l_en:
            lines.append((ln, f_en, (240, 250, 255), y)); y += h_en
    if src and src != "Cacique":
        lines.append((src, f_src, (230, 243, 252), y + 28))
    sd = ImageDraw.Draw(shade)
    for ln, fnt, _, yy in lines:           # soft shadow so the words read on any background
        sd.text(((W - draw.textlength(ln, font=fnt)) / 2 + 3, yy + 4), ln, font=fnt, fill=(0, 30, 60, 160))
    shade = shade.filter(ImageFilter.GaussianBlur(6))
    im = Image.alpha_composite(im, shade)
    draw = ImageDraw.Draw(im)
    for ln, fnt, color, yy in lines:
        draw.text(((W - draw.textlength(ln, font=fnt)) / 2, yy), ln, font=fnt, fill=color)
    sig = "Cacique Diario"
    f_sig = font("regular", 26)
    draw.text((W - pad_x - draw.textlength(sig, font=f_sig), H - 70), sig, font=f_sig, fill=(255, 255, 255, 200))
    im.convert("RGB").save(out_file, "JPEG", quality=90)


def one_language(m, lang):
    """The message in one language ('es' or 'en'), or both ('es+en')."""
    if lang == "es+en":
        return m
    src, k = m.get("fuente", ""), m.get("fuente", "").find(" · ")
    if k >= 0:
        src = src[k + 3:] if lang == "en" else src[:k]
    text = (m.get("en") or m.get("es")) if lang == "en" else m.get("es")
    return dict(m, es=text, en="", fuente=src)


def make_cards(day, msgs):
    """Picture cards for the shared family messages. Returns the files (empty if Pillow is missing)."""
    import importlib.util
    if importlib.util.find_spec("PIL") is None:
        print("  ! python3-pil is not installed: no picture cards (fix: sudo apt install -y python3-pil)", file=sys.stderr)
        return []
    folder = path("imagenes", day.isoformat())
    os.makedirs(folder, exist_ok=True)
    photos = []
    fondos = settings().get("fondos") or ""
    if fondos and os.path.isdir(os.path.expanduser(fondos)):
        for ext in ("jpg", "jpeg", "png", "JPG", "JPEG", "PNG"):
            photos += glob.glob(os.path.join(os.path.expanduser(fondos), "**", "*." + ext), recursive=True)
    rng = random.Random(day.isoformat())
    lang = people()["familia"].get("idioma", "es")       # the cards speak the family's language (one, unless "both")
    files = []
    for i, m in enumerate([m for m in msgs if not m.get("recordatorio")]):
        m = one_language(m, lang)
        f = os.path.join(folder, "diario-%s-%d-%s.jpg" % (day.isoformat(), i + 1, lang.replace("+", "")))
        if not os.path.exists(f):
            card(m, f, rng, photos)
        files.append(f)
    return files


# ================================================================ CaciquePhotos (Immich): the "Cacique Diario" album
def at_home(url):
    """True only for addresses inside the house: this computer, 192.168.x.x / 10.x / 172.16-31.x, or a .home name."""
    import ipaddress
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if host in ("localhost",) or host.endswith(".home") or host.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback
    except ValueError:
        return False


def immich(method, api_path, body=None, data=None, ctype=None, timeout=60):
    s = settings()
    if not s.get("immich_key"):
        raise RuntimeError("no CaciquePhotos key")
    if not at_home(s["immich_url"]) or not at_home(OLLAMA):
        raise RuntimeError("CaciquePhotos must be an address inside the house")
    headers = {"x-api-key": s["immich_key"], "Accept": "application/json"}
    if body is not None:
        data, ctype = json.dumps(body).encode(), "application/json"
    if ctype:
        headers["Content-Type"] = ctype
    req = urllib.request.Request(s["immich_url"].rstrip("/") + "/api" + api_path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode() or "null"
    return json.loads(raw)


def album_id(name):
    for a in immich("GET", "/albums") or []:
        if a.get("albumName") == name:
            return a["id"]
    return immich("POST", "/albums", {"albumName": name,
                                      "description": "Mensajes del día de la casa · The home's messages of the day"})["id"]


def multipart(fields, file_field, file_path):
    boundary = "----cacique" + uuid.uuid4().hex
    out = io.BytesIO()
    for k, v in fields.items():
        out.write(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (boundary, k, v)).encode())
    out.write(("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\nContent-Type: image/jpeg\r\n\r\n"
               % (boundary, file_field, os.path.basename(file_path))).encode())
    out.write(open(file_path, "rb").read())
    out.write(("\r\n--%s--\r\n" % boundary).encode())
    return out.getvalue(), "multipart/form-data; boundary=" + boundary


def upload(file_path):
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    fields = {"fileCreatedAt": now, "fileModifiedAt": now, "isFavorite": "false"}
    try:
        data, ctype = multipart(fields, "assetData", file_path)
        return immich("POST", "/assets", data=data, ctype=ctype)["id"]
    except urllib.error.HTTPError as e:
        if e.code != 400:
            raise
        # older Immich versions also want these two fields
        fields.update(deviceAssetId="cacique-diario-" + os.path.basename(file_path), deviceId="cacique-diario")
        data, ctype = multipart(fields, "assetData", file_path)
        return immich("POST", "/assets", data=data, ctype=ctype)["id"]


def remove_assets(ids, album_ids):
    for aid in album_ids:
        try:
            immich("DELETE", "/albums/%s/assets" % aid, {"ids": ids})
        except Exception:
            pass
    try:
        immich("DELETE", "/assets", {"ids": ids, "force": False})   # to Immich's trash, not erased
    except Exception:
        pass


def to_photos(day, files):
    """Put today's cards in the album(s) and take out the ones older than 'guardar_dias'. Returns a short note."""
    s = settings()
    if not s.get("immich_key"):
        return "sin clave de CaciquePhotos (ponla en /admin → Ajustes) · no CaciquePhotos key yet"
    st = load("immich.json", {"subidos": {}})
    names = [ALBUM] + [n.strip() for n in (s.get("albumes_extra") or "").split(",") if n.strip()]
    ids = {n: album_id(n) for n in names}
    key = day.isoformat()
    if key not in st["subidos"]:
        assets = [upload(f) for f in files]
        for aid in ids.values():
            if assets:
                immich("PUT", "/albums/%s/assets" % aid, {"ids": assets})
        st["subidos"][key] = assets
    keep = int(s.get("guardar_dias") or 7)
    old = [d for d in st["subidos"] if (day - dt.date.fromisoformat(d)).days >= keep]
    gone = [a for d in old for a in st["subidos"][d]]
    if gone:
        remove_assets(gone, ids.values())
        for d in old:
            del st["subidos"][d]
    save("immich.json", st)
    return "%d tarjetas en el álbum \"%s\" · cards in the album" % (len(files), ALBUM)


# ================================================================ optional: new messages from the local AI
def ai_suggest(per_theme=2):
    """Ask CaciqueGuía's local AI for new messages; they wait for an adult in the approval page."""
    if not settings().get("ia"):
        return "IA apagada · AI off"
    if not at_home(OLLAMA):
        return "IA fuera de la casa: no se usa · AI outside the house: not used"
    try:
        urllib.request.urlopen(OLLAMA + "/api/tags", timeout=3).read()
    except Exception:
        return "IA no disponible (CaciqueGuía apagada) · AI not running"
    queue = load("cola.json", [])
    examples = {}
    for it in usable():
        examples.setdefault(it["tema"], []).append(it["es"])
    added = 0
    for tema, (es_name, en_name) in TEMAS.items():
        if tema == "casa":
            continue
        ex = "\n".join("- " + e for e in examples.get(tema, [])[:5])
        prompt = ("Eres el asistente de una familia puertorriqueña cristiana. Escribe %d mensajes cortos y positivos "
                  "para el tema \"%s\" (%s), para mostrar en la pantalla de la casa. Máximo 25 palabras cada uno. "
                  "Español de Puerto Rico, cálido, sin regaños, sin citar versículos bíblicos.\nEjemplos del estilo:\n%s\n"
                  "Responde SOLO con JSON: [{\"es\": \"...\", \"en\": \"English translation\"}]") % (per_theme, es_name, en_name, ex)
        try:
            req = urllib.request.Request(OLLAMA + "/api/generate", data=json.dumps(
                {"model": MODEL, "prompt": prompt, "stream": False, "format": "json"}).encode(),
                headers={"Content-Type": "application/json"})
            raw = json.loads(urllib.request.urlopen(req, timeout=240).read().decode()).get("response", "")
            got = json.loads(raw)
            if isinstance(got, dict):
                got = next((v for v in got.values() if isinstance(v, list)), [got])
            for g in got[:per_theme]:
                es, en = str(g.get("es", "")).strip(), str(g.get("en", "")).strip()
                if 8 <= len(es) <= 220:
                    queue.append({"id": "ia-%s" % uuid.uuid4().hex[:10], "tema": tema, "es": es, "en": en,
                                  "para": "todos", "fuente": "Cacique (IA)", "verificar": True})
                    added += 1
        except Exception as e:
            print("  ! AI (%s): %s" % (tema, e), file=sys.stderr)
    save("cola.json", queue)
    return "%d mensajes nuevos de la IA esperan aprobación · new AI messages await approval" % added


# ================================================================ the daily job
def run_day(day=None, force=False):
    day = day or dt.date.today()
    with DAY_LOCK:
        log = load("registro.json", {})
        if log.get("ultimo") == day.isoformat() and not force:
            return log
        if force:
            cache = path("dias", day.isoformat() + ".json")
            if os.path.exists(cache):
                os.remove(cache)
            for f in glob.glob(path("imagenes", day.isoformat(), "*.jpg")):
                os.remove(f)
            st = load("immich.json", {"subidos": {}})
            redo = st["subidos"].pop(day.isoformat(), None)
            if redo:
                try:      # take today's earlier cards out of the albums before adding the new ones
                    s = settings()
                    names = [ALBUM] + [n.strip() for n in (s.get("albumes_extra") or "").split(",") if n.strip()]
                    remove_assets(redo, [album_id(n) for n in names])
                except Exception as e:
                    print("  ! could not take out today's old cards:", e, file=sys.stderr)
            save("immich.json", st)
        notes = []
        for pid in people():
            pick(pid, day)
        files = make_cards(day, pick("familia", day))
        notes.append("%d tarjetas dibujadas · cards drawn" % len(files))
        try:
            notes.append(to_photos(day, files))
        except Exception as e:
            notes.append("CaciquePhotos: %s" % e)
        for old in glob.glob(path("imagenes", "*")):      # keep 14 days of cards on the disk
            try:
                if (day - dt.date.fromisoformat(os.path.basename(old))).days > 14:
                    for f in glob.glob(os.path.join(old, "*")):
                        os.remove(f)
                    os.rmdir(old)
            except ValueError:
                pass
        log = {"ultimo": day.isoformat(), "hora": time.strftime("%H:%M"), "notas": notes}
        save("registro.json", log)
        print("  Cacique Diario %s: %s" % (day, " · ".join(notes)), flush=True)
    threading.Thread(target=lambda: save("registro.json", dict(load("registro.json", {}), ia=ai_suggest())),
                     daemon=True).start()
    return log


def scheduler():
    while True:
        try:
            now = dt.datetime.now()
            if load("registro.json", {}).get("ultimo") != now.date().isoformat() and now.hour >= int(settings()["hora"]):
                run_day(now.date())
        except Exception as e:
            print("  ! daily job:", e, file=sys.stderr, flush=True)
        time.sleep(60)


# ================================================================ presence: which home devices are on the Wi-Fi (for routines)
# Off until an adult turns it on (Ajustes). Every 2 minutes it asks the home network "who's here?" (ARP, like the
# router's own device list), writes arrivals and departures to presencia/<year-month>.csv, and keeps nothing else.
# Adults name each device and say whose it is; after a few weeks the page shows each person's usual
# leave / arrive times, so morning messages can be waiting for them. Nothing leaves the house.
AWAY_AFTER = 10 * 60          # a device counts as gone after 10 minutes without answering (phones doze)


def lan():
    """(device, network address like 192.168.1.) of the house connection, or (None, None)."""
    try:
        import subprocess
        r = subprocess.run(["ip", "-4", "-o", "addr", "show", "scope", "global"], capture_output=True, text=True, timeout=5).stdout
        for line in r.splitlines():
            f = line.split()
            if len(f) > 3 and not re.match(r"(docker|br-|veth|virbr|tailscale|lo)", f[1]):
                ip, prefix = f[3].split("/")
                if prefix == "24":
                    return f[1], ip.rsplit(".", 1)[0] + "."
    except Exception:
        pass
    return None, None


def neighbors(dev, net):
    """{mac: ip} of the devices that answer right now."""
    import socket, subprocess
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.01)
    for i in range(1, 255):                     # one tiny packet each: the computer asks "who has this number?"
        try:
            sock.sendto(b"", (net + str(i), 9))
        except OSError:
            pass
    sock.close()
    time.sleep(12)                              # give every device time to answer (or to be marked failed)
    out = subprocess.run(["ip", "-j", "neigh", "show", "dev", dev], capture_output=True, text=True, timeout=10).stdout
    here = {}
    for n in json.loads(out or "[]"):
        state = n.get("state") or []
        if n.get("lladdr") and any(st in ("REACHABLE", "PERMANENT") for st in state):
            here[n["lladdr"].lower()] = n.get("dst", "")
    return here


# ---- privacy: everything the recorder writes is ENCRYPTED on this computer's disk, and never goes to GitHub
# (it lives in ~/elcaciquedeck-data, outside the project folder). The key is made here, on first use, and stays here:
# ~/elcaciquedeck-data/keys/diario.key (only this user can read it). Copy it to paper/USB for the safe: without it,
# the recordings can't be read on another computer. If python3-cryptography is missing, NOTHING is recorded.
KEY_FILE = os.path.join(os.path.expanduser("~"), "elcaciquedeck-data", "keys", "diario.key")


def vault():
    from cryptography.fernet import Fernet      # AES + a seal against changes (python3-cryptography)
    if not os.path.exists(KEY_FILE):
        os.makedirs(os.path.dirname(KEY_FILE), mode=0o700, exist_ok=True)
        fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(Fernet.generate_key())
    return Fernet(open(KEY_FILE, "rb").read().strip())


def can_encrypt():
    try:
        vault()
        return True
    except Exception:
        return False


def load_secret(name, default):
    try:
        return json.loads(vault().decrypt(open(path(name + ".enc"), "rb").read()).decode())
    except FileNotFoundError:
        return default
    except Exception as e:
        print("  ! could not read %s.enc: %s" % (name, e), file=sys.stderr)
        return default


def save_secret(name, value):
    os.makedirs(DATA, exist_ok=True)
    tmp = path(name + ".enc.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(vault().encrypt(json.dumps(value, ensure_ascii=False).encode()))
    os.replace(tmp, path(name + ".enc"))


def log_event(kind, who, event, ip="", when=None):
    """One arrival/departure, as one encrypted line in presencia/<year-month>.log.enc"""
    os.makedirs(path("presencia"), mode=0o700, exist_ok=True)
    stamp = time.localtime(when) if when else time.localtime()
    f = path("presencia", time.strftime("%Y-%m", stamp) + ".log.enc")
    line = "%s,%s,%s,%s,%s" % (time.strftime("%Y-%m-%d %H:%M:%S", stamp), kind, who, event, ip)
    fd = os.open(f, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "ab") as h:
        h.write(vault().encrypt(line.encode()) + b"\n")


def read_events():
    v = vault()
    for f in sorted(glob.glob(path("presencia", "*.log.enc"))):
        for tok in open(f, "rb").read().split(b"\n"):
            if tok.strip():
                try:
                    yield v.decrypt(tok.strip()).decode()
                except Exception:
                    continue


def presence_step(here, now=None):
    """Update who is home from one look at the network; write arrivals/departures."""
    now = now or time.time()
    st = load_secret("presencia", {"equipos": {}, "personas": {}})
    eq = st.setdefault("equipos", {})
    for mac, ip in here.items():
        d = eq.setdefault(mac, {"primera_vez": now})
        if not d.get("aqui"):
            log_event("equipo", mac, "llega", ip, now)
        d.update(aqui=True, visto=now, ip=ip)
    for mac, d in eq.items():
        if d.get("aqui") and mac not in here and now - d.get("visto", 0) > AWAY_AFTER:
            d["aqui"] = False
            log_event("equipo", mac, "sale", d.get("ip", ""), d.get("visto"))     # left right after it was last seen
    names = load_secret("equipos", {})          # {mac: {"nombre": ..., "persona": pid}}
    per = st.setdefault("personas", {})
    owners = {}
    for mac, info in names.items():
        if info.get("persona"):
            owners.setdefault(info["persona"], []).append(mac)
    for pid, macs in owners.items():
        home = any(eq.get(m, {}).get("aqui") for m in macs)
        if per.get(pid) is None:
            per[pid] = home
        elif per[pid] != home:
            per[pid] = home
            last = max(eq.get(m, {}).get("visto", now) for m in macs)
            log_event("persona", pid, "llega" if home else "sale", "", now if home else last)
    save_secret("presencia", st)


def routines(weeks=8):
    """Each person's usual weekday times: first departure in the morning, return in the afternoon (medians)."""
    first_out, back = {}, {}
    since = dt.date.today() - dt.timedelta(weeks=weeks)
    for line in read_events():
        try:
            t, kind, who, ev, _ = line.split(",", 4)
            when = dt.datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        if kind != "persona" or when.date() < since or when.weekday() > 4:
            continue
        mins = when.hour * 60 + when.minute
        if ev == "sale" and 180 <= mins <= 660:
            first_out.setdefault(who, {}).setdefault(when.date(), mins)
        if ev == "llega" and 720 <= mins <= 1320:
            back.setdefault(who, {}).setdefault(when.date(), mins)

    def median(vals):
        v = sorted(vals)
        return v[len(v) // 2] if v else None
    out = {}
    for who in set(first_out) | set(back):
        o, b = list(first_out.get(who, {}).values()), list(back.get(who, {}).values())
        out[who] = {"sale": median(o), "dias_sale": len(o), "llega": median(b), "dias_llega": len(b)}
    return out


def presence_loop():
    while True:
        try:
            if settings().get("presencia") and can_encrypt():      # never records without encryption
                dev, net = lan()
                if dev:
                    presence_step(neighbors(dev, net))
        except Exception as e:
            print("  ! presence:", e, file=sys.stderr, flush=True)
        time.sleep(120)


# ================================================================ pages
STYLE = """
:root{--ink:#0d3b5c;--sub:#3e6c8a;--glass:rgba(255,255,255,.55);--edge:rgba(255,255,255,.85);--ok:#1e8a4c;--no:#b3392f}
*{box-sizing:border-box}html,body{margin:0;height:100%}
body{font-family:"Segoe UI",Ubuntu,"Noto Sans",system-ui,sans-serif;color:var(--ink);
 background:linear-gradient(180deg,#5aa9e6 0%,#9fdcf2 45%,#bfe8c4 80%,#8fd08e 100%);background-attachment:fixed}
"""

SHOW = """<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cacique Diario</title><style>""" + STYLE + """
body{display:flex;flex-direction:column;overflow:hidden}
.top{display:flex;justify-content:space-between;align-items:center;padding:3vh 4vw 0;font-size:clamp(16px,2.2vw,30px);color:#fff;
 text-shadow:0 2px 8px rgba(0,40,80,.35)}
.top b{font-weight:600}
main{flex:1;display:flex;align-items:center;justify-content:center;padding:3vh 5vw}
.card{max-width:1400px;width:100%;padding:5vh 5vw;border-radius:clamp(24px,3vw,48px);background:var(--glass);
 border:2px solid var(--edge);box-shadow:0 20px 60px rgba(0,50,90,.25),inset 0 1px 0 #fff;backdrop-filter:blur(14px);
 text-align:center;transition:opacity .8s}
.tema{display:inline-block;padding:.35em 1em;border-radius:999px;background:rgba(255,255,255,.7);font-size:clamp(14px,1.6vw,24px);
 color:var(--sub);margin-bottom:3vh}
.es{font-size:clamp(28px,4.6vw,76px);font-weight:700;line-height:1.18;margin:0}
.en{font-size:clamp(18px,2.4vw,40px);font-style:italic;color:var(--sub);margin:3vh 0 0}
.src{font-size:clamp(14px,1.5vw,24px);color:var(--sub);margin-top:3vh}
.dots{display:flex;gap:10px;justify-content:center;padding:0 0 4vh}
.dots i{width:12px;height:12px;border-radius:50%;background:rgba(255,255,255,.5)}.dots i.on{background:#fff}
.hide{opacity:0}
body.espejo{background:#000}body.espejo .card{background:none;border:none;box-shadow:none;backdrop-filter:none}
body.espejo,body.espejo .top{color:#fff;text-shadow:none}body.espejo .en,body.espejo .src,body.espejo .tema{color:#bbb;background:none}
body.espejo .dots i{background:#333}body.espejo .dots i.on{background:#ddd}
body.solo-es .en{display:none}body.solo-en .es{display:none}body.solo-en .en{font-size:clamp(28px,4.6vw,76px);font-style:normal;color:inherit}
</style></head><body>
<div class="top"><span id="hello"></span><b id="clock"></b></div>
<main><div class="card" id="card"><div class="tema" id="tema"></div><p class="es" id="es">Cacique Diario</p>
<p class="en" id="en" lang="en"></p><div class="src" id="src"></div></div></main>
<div class="dots" id="dots"></div>
<script>
const q=new URLSearchParams(location.search),para=q.get("para")||"familia",modo=q.get("modo")||"",lang=q.get("idioma")||"";
const SEC=+(q.get("segundos")||20), TEMAS=%TEMAS%;
if(modo)document.body.classList.add(modo);
function setLang(l){document.body.classList.remove("solo-es","solo-en");if(l==="es"||l==="en")document.body.classList.add("solo-"+l);document.documentElement.lang=l==="en"?"en":"es";}
setLang(lang||"es");
let M=[],i=0;const $=id=>document.getElementById(id);
function greet(){const h=new Date().getHours();return h<12?["Buenos días","Good morning"]:h<19?["Buenas tardes","Good afternoon"]:["Buenas noches","Good evening"];}
const EN=()=>document.body.classList.contains("solo-en"), BOTH=()=>!document.body.classList.contains("solo-en")&&!document.body.classList.contains("solo-es");
const W=(a)=>EN()?a[1]:BOTH()?a[0]+" · "+a[1]:a[0];
function clock(){const n=new Date(),loc=EN()?"en-US":"es-PR";let d;try{d=n.toLocaleDateString(loc,{weekday:"long",day:"numeric",month:"long"})+" · "+n.toLocaleTimeString(loc,{hour:"numeric",minute:"2-digit"})}catch(e){d=n.toString()}
 $("clock").textContent=d.charAt(0).toUpperCase()+d.slice(1);const g=W(greet());$("hello").textContent=M.nombre?g+", "+M.nombre:g;}
function show(){if(!M.mensajes||!M.mensajes.length)return;const m=M.mensajes[i%M.mensajes.length];$("card").classList.add("hide");
 setTimeout(()=>{const t=m.recordatorio?["Recordatorio","Reminder"]:(TEMAS[m.tema]||["",""]);$("tema").textContent=W(t);
  $("es").textContent=m.es;$("en").textContent=m.en||"";const f=!m.recordatorio&&m.fuente&&m.fuente!=="Cacique"?m.fuente:"",k=f.indexOf(" · ");$("src").textContent=k<0||BOTH()?f:EN()?f.slice(k+3):f.slice(0,k);
  $("dots").innerHTML=M.mensajes.map((_,k)=>`<i class="${k===i%M.mensajes.length?"on":""}"></i>`).join("");$("card").classList.remove("hide");i++;},700);}
async function load(){try{const r=await fetch("/api/hoy?para="+encodeURIComponent(para),{cache:"no-store"});M=await r.json();
 if(!lang)setLang(M.idioma||"es");clock();if(i===0)show();}catch(e){}}
load();setInterval(load,600000);setInterval(show,SEC*1000);clock();setInterval(clock,30000);
</script></body></html>"""


def esc(s):
    return html.escape(str(s or ""), quote=True)


def admin_page(tab, msg=""):
    s, ps = settings(), people()
    dec = load("decisiones.json", {})
    tabs = [("pendientes", "Por aprobar · To approve"), ("hoy", "Hoy · Today"), ("personas", "Personas · People"),
            ("recordatorios", "Recordatorios · Reminders"), ("propios", "Mis mensajes · My messages"), ("equipos", "Equipos y rutinas · Devices & routines"),
            ("ajustes", "Ajustes · Settings")]
    nav = "".join('<a class="%s" href="/admin?t=%s">%s</a>' % ("on" if k == tab else "", k, v) for k, v in tabs)
    body = ""
    tema_opts = lambda sel="": "".join('<option value="%s"%s>%s · %s</option>' % (k, " selected" if k == sel else "", a, b) for k, (a, b) in TEMAS.items())
    para_opts = '<option value="todos">Todos (pantallas compartidas) · Everyone</option>' + "".join(
        '<option value="%s">%s · %s</option>' % (k, a, b) for k, (a, b) in ROLES.items())
    if tab == "pendientes":
        rows = [it for it in library() if status_of(it, dec) == "pendiente"] + load("cola.json", [])
        body += "<h2>Por aprobar · Waiting for an adult</h2><p class='sub'>Versículos: compáralos con tu Biblia. Mensajes de la IA: léelos y corrígelos si hace falta. Nada de esto sale en las pantallas hasta que lo apruebes. · Verses: compare with your Bible. AI messages: read and fix. Nothing here is shown until approved.</p>"
        if not rows:
            body += "<p class='empty'>Nada pendiente. · Nothing waiting.</p>"
        for it in rows:
            body += """<form method="post" action="/admin/decidir" class="item"><input type="hidden" name="id" value="%s">
<div class="meta">%s – %s – <i>%s</i></div><textarea name="es" rows="2">%s</textarea><textarea name="en" rows="2" lang="en">%s</textarea>
<div class="row"><button name="d" value="ok" class="ok">Aprobar · Approve</button><button name="d" value="no" class="no">Rechazar · Reject</button></div></form>""" % (
                esc(it["id"]), esc(TEMAS.get(it["tema"], ("", ""))[0]), esc(it.get("para", "todos")), esc(it.get("fuente")), esc(it["es"]), esc(it.get("en")))
    elif tab == "hoy":
        day = dt.date.today()
        reg = load("registro.json", {})
        body += "<h2>Hoy · Today <small>%s</small></h2><p class='sub'>Último trabajo diario · Last daily run: <b>%s %s</b></p><div class='sub'>%s</div>" % (
            day.isoformat(), esc(reg.get("ultimo", "—")), esc(reg.get("hora", "")),
            "".join("<div>%s</div>" % esc(n) for n in reg.get("notas", []) + ([reg["ia"]] if reg.get("ia") else [])))
        body += '<form method="post" action="/admin/rehacer"><button>Rehacer hoy (mensajes, tarjetas y álbum) · Redo today</button></form>'
        for pid, p in ps.items():
            body += "<h3>%s <a class='lnk' href='/?para=%s' target='_blank'>abrir pantalla · open screen</a></h3><ul>" % (esc(p.get("nombre", pid)), esc(pid))
            for m in pick(pid, day):
                body += "<li><b>%s</b> <span lang='en'>%s</span></li>" % (esc(m["es"]), esc(m.get("en")))
            body += "</ul>"
        imgs = sorted(glob.glob(path("imagenes", day.isoformat(), "*.jpg")))
        if imgs:
            body += "<h3>Tarjetas de hoy · Today's cards</h3><div class='cards'>" + "".join(
                "<img src='/tarjeta/%s/%s' alt=''>" % (day.isoformat(), esc(os.path.basename(f))) for f in imgs) + "</div>"
    elif tab == "personas":
        body += ("<h2>Personas · People</h2><p class='sub'><span class='es'>Cada persona tiene su pantalla: <code>http://&lt;servidor&gt;:8097/?para=&lt;nombre&gt;</code>. "
                 "Los roles deciden qué mensajes personales recibe (por ejemplo, <i>esposo</i>). Las pantallas compartidas y la portada usan <b>Familia</b>.</span>"
                 "<span class='en'>Each person gets a screen: <code>http://&lt;server&gt;:8097/?para=&lt;name&gt;</code>. Roles decide which personal messages "
                 "they get (for example, <i>husband</i>). Shared screens and the front page use <b>Familia</b>.</span></p>")
        for pid, p in ps.items():
            roles = "".join('<label><input type="checkbox" name="roles" value="%s"%s> %s</label>' % (k, " checked" if k in p.get("roles", []) else "", a) for k, (a, b) in ROLES.items())
            temas = "".join('<label><input type="checkbox" name="temas" value="%s"%s> %s</label>' % (k, " checked" if k in p.get("temas", TEMAS) else "", a) for k, (a, b) in TEMAS.items())
            idi = "".join('<option value="%s"%s>%s</option>' % (k, " selected" if p.get("idioma", "es") == k else "", v) for k, v in (("es", "Español"), ("en", "English"), ("es+en", "Los dos · Both")))
            body += """<form method="post" action="/admin/persona" class="item"><input type="hidden" name="id" value="%s">
<div class="meta"><b>%s</b> – <a class="lnk" href="/?para=%s%s" target="_blank">pantalla · screen</a> – <a class="lnk" href="/?para=%s&modo=espejo" target="_blank">espejo · mirror</a></div>
<label>Nombre · Name <input name="nombre" value="%s"></label>
<div class="checks"><span>Roles:</span>%s</div><div class="checks"><span>Temas · Themes:</span>%s</div>
<label>Mensajes por día · per day <input name="por_dia" type="number" min="1" max="8" value="%s"></label>
<label>Idioma · Language <select name="idioma">%s</select></label>
<div class="row"><button class="ok">Guardar · Save</button>%s</div></form>""" % (
                esc(pid), esc(pid), esc(pid), "&idioma=" + esc(p.get("idioma")) if p.get("idioma") in ("es", "en") else "", esc(pid),
                esc(p.get("nombre", pid)), roles if pid != "familia" else "<i>pantallas compartidas: solo mensajes para todos · shared screens: messages for everyone only</i>", temas,
                esc(p.get("por_dia") or s["por_dia"]), idi,
                '<button name="borrar" value="1" class="no">Quitar · Remove</button>' if pid != "familia" else "")
        body += """<form method="post" action="/admin/persona" class="item new"><div class="meta"><b>Añadir persona · Add a person</b></div>
<label>Nombre · Name <input name="nombre" required placeholder="Ej.: Abuela"></label><div class="row"><button class="ok">Añadir · Add</button></div></form>"""
    elif tab == "recordatorios":
        body += "<h2>Recordatorios de la semana · Weekly reminders</h2><p class='sub'>Salen primero en las pantallas ese día. · Shown first on those days.</p>"
        for i, r in enumerate(load("recordatorios.json", [])):
            days = ", ".join(DIAS[d] for d in r.get("dias", []))
            body += """<form method="post" action="/admin/recordatorio" class="item"><input type="hidden" name="i" value="%d">
<div class="meta">%s – %s %s</div><b>%s</b><br><span lang="en">%s</span>
<div class="row"><button name="borrar" value="1" class="no">Quitar · Remove</button></div></form>""" % (
                i, esc(days), esc(r.get("para", "todos")), "" if r.get("activo", True) else "(apagado)", esc(r["es"]), esc(r.get("en")))
        checks = "".join('<label><input type="checkbox" name="dias" value="%d"> %s</label>' % (i, d) for i, d in enumerate(DIAS))
        body += """<form method="post" action="/admin/recordatorio" class="item new"><div class="meta"><b>Nuevo recordatorio · New reminder</b></div>
<div class="checks">%s</div><label>Español <input name="es" required placeholder="Hoy es miércoles: saquemos la basura."></label>
<label>English <input name="en" placeholder="It's Wednesday: let's take out the trash."></label>
<label>Para · For <select name="para">%s</select></label><div class="row"><button class="ok">Guardar · Save</button></div></form>""" % (checks, para_opts)
    elif tab == "propios":
        own = load("propios.json", [])
        body += "<h2>Mis mensajes · My own messages</h2><p class='sub'>Escríbelos tú: salen aprobados. · Written by you: approved right away.</p>"
        body += """<form method="post" action="/admin/propio" class="item new"><label>Tema · Theme <select name="tema">%s</select></label>
<label>Para · For <select name="para">%s</select></label><label>Español <textarea name="es" rows="2" required></textarea></label>
<label>English <textarea name="en" rows="2"></textarea></label><label>Fuente · Source <input name="fuente" placeholder="Cacique"></label>
<div class="row"><button class="ok">Añadir · Add</button></div></form>""" % (tema_opts(), para_opts)
        for it in reversed(own):
            body += """<form method="post" action="/admin/propio" class="item"><input type="hidden" name="borrar" value="%s"><div class="meta">%s – %s</div>
<b>%s</b><br><span lang="en">%s</span><div class="row"><button class="no">Quitar · Remove</button></div></form>""" % (
                esc(it["id"]), esc(TEMAS.get(it["tema"], ("", ""))[0]), esc(it.get("para")), esc(it["es"]), esc(it.get("en")))
    elif tab == "equipos":
        on = s.get("presencia")
        body += ("<h2>Equipos y rutinas · Devices &amp; routines</h2><p class='sub'><span class='es'>Cada 2 minutos El Cacique mira qué equipos están "
                 "en el Wi-Fi de la casa (como la lista de equipos del router). Ponle nombre a cada uno y di de quién es. Después de unas semanas, aquí "
                 "salen las horas de cada persona, para que los mensajes de la mañana la estén esperando. Nada sale de la casa.</span>"
                 "<span class='en'>Every 2 minutes El Cacique looks at which devices are on the home Wi-Fi (like the router's device list). Name each "
                 "one and say whose it is. After a few weeks, each person's usual times show here, so morning messages can be waiting for them. "
                 "Nothing leaves the house.</span></p>")
        body += """<form method="post" action="/admin/presencia" class="item"><div class="meta"><b>%s</b></div>
<div class="row"><button name="on" value="%s" class="%s">%s</button></div></form>""" % (
            "Registro encendido · Recording is on" if on else "Registro apagado · Recording is off",
            "0" if on else "1", "no" if on else "ok", "Apagar · Turn off" if on else "Encender · Turn on")
        st, names = (load_secret("presencia", {"equipos": {}}), load_secret("equipos", {})) if can_encrypt() else ({"equipos": {}}, {})
        if not can_encrypt():
            body += "<p class='note'>Falta python3-cryptography: no se graba nada sin cifrar. · python3-cryptography is missing: nothing is recorded without encryption. (sudo apt install -y python3-cryptography)</p>"
        rt = routines() if can_encrypt() else {}
        if rt:
            body += "<h3>Rutinas (lunes a viernes, últimas 8 semanas) · Routines (weekdays, last 8 weeks)</h3><ul>"
            hm = lambda m: "—" if m is None else "%d:%02d %s" % ((m // 60 - 1) % 12 + 1, m % 60, "a. m." if m < 720 else "p. m.")
            for who, r in rt.items():
                body += "<li><b>%s</b><br><span>Sale · Leaves</span> <b>%s</b> (%d <span>días · days</span>) – <span>Llega · Arrives</span> <b>%s</b> (%d <span>días · days</span>)</li>" % (
                    esc(ps.get(who, {}).get("nombre", who)), hm(r["sale"]), r["dias_sale"], hm(r["llega"]), r["dias_llega"])
            body += "</ul>"
        eq = sorted(st.get("equipos", {}).items(), key=lambda kv: -kv[1].get("visto", 0))
        if not eq:
            body += "<p class='empty'>Todavía no hay equipos. · No devices yet.</p>"
        person_opts = lambda sel: '<option value="">Nadie (es de la casa) · Nobody (the house)</option>' + "".join(
            '<option value="%s"%s>%s</option>' % (esc(pid), " selected" if pid == sel else "", esc(p.get("nombre", pid))) for pid, p in ps.items() if pid != "familia")
        for mac, d in eq:
            n = names.get(mac, {})
            seen = time.strftime("%d/%m %H:%M", time.localtime(d.get("visto", 0)))
            body += """<form method="post" action="/admin/equipo" class="item"><input type="hidden" name="mac" value="%s">
<div class="meta"><span>%s</span> – %s – <code>%s</code> – <span>%s</span> %s</div><label>Nombre del equipo · Device name <input name="nombre" value="%s" placeholder="Teléfono, TV, enchufe…"></label>
<label>De quién es · Whose is it <select name="persona">%s</select></label><div class="row"><button class="ok">Guardar · Save</button></div></form>""" % (
                esc(mac), "🟢 en casa · home" if d.get("aqui") else "⚪ fuera · away", esc(d.get("ip", "")), esc(mac),
                "visto · seen", esc(seen), esc(n.get("nombre", "")), person_opts(n.get("persona", "")))
    elif tab == "ajustes":
        body += """<h2>Ajustes · Settings</h2><form method="post" action="/admin/ajustes" class="item">
<label>Clave de CaciquePhotos (Immich → tu foto → Configuración de la cuenta → Claves API → Nueva) · CaciquePhotos API key
<input name="immich_key" type="password" autocomplete="off" placeholder="%s"></label>
<label>Dirección de CaciquePhotos · address <input name="immich_url" value="%s"></label>
<label>Álbumes extra donde también van las tarjetas (separados por coma) · Extra albums for the cards <input name="albumes_extra" value="%s" placeholder="Familia Abierta"></label>
<label>Tarjetas por día (Familia) · Cards per day <input name="por_dia" type="number" min="1" max="6" value="%s"></label>
<label>Hora del trabajo diario (0-23) · Daily job hour <input name="hora" type="number" min="0" max="23" value="%s"></label>
<label>Días que una tarjeta se queda en el álbum · Days a card stays <input name="guardar_dias" type="number" min="1" max="60" value="%s"></label>
<label>Carpeta con fotos propias para el fondo (opcional) · Your own background photos folder <input name="fondos" value="%s" placeholder="/media/usuario/Library/Diario/fondos"></label>
<label class="inline"><input type="checkbox" name="ia" value="1"%s> Pedirle mensajes nuevos a la IA de la casa cada noche (si CaciqueGuía está prendida) · Ask the home AI for new messages nightly</label>
<div class="row"><button class="ok">Guardar · Save</button></div></form>""" % (
            "guardada - escribe otra para cambiarla" if s.get("immich_key") else "pega la clave aquí", esc(s["immich_url"]), esc(s["albumes_extra"]),
            esc(s["por_dia"]), esc(s["hora"]), esc(s["guardar_dias"]), esc(s["fondos"]), " checked" if s.get("ia") else "")
    note = "<div class='note'>%s</div>" % "".join("<div>%s</div>" % esc(x) for x in msg.split("\n")) if msg else ""
    return ADMIN_SHELL.replace("{{NAV}}", nav).replace("{{BODY}}", note + body)


# one language at a time on the adults' pages: "Español · English" texts keep one side (ES/EN switch, remembered)
LANGJS = r"""<script>
(function(){var L;try{L=localStorage.getItem("cq-lang")}catch(e){}
 L=L||((navigator.language||"es").toLowerCase().indexOf("en")===0?"en":"es");var O=new WeakMap();
 function side(o){var k=o.indexOf(" · ");if(k<0)return o;var t=(L==="en"?o.slice(k+3):o.slice(0,k)).trim();
  if(/:\s*$/.test(o)&&!/:$/.test(t))t+=":";return o.match(/^\s*/)[0]+t+o.match(/\s*$/)[0];}
 function walk(n){if(n.nodeType===3){var o=O.has(n)?O.get(n):n.nodeValue;if(o.indexOf(" · ")<0)return;O.set(n,o);n.nodeValue=side(o);return;}
  if(n.nodeType!==1||/^(TEXTAREA|SCRIPT|STYLE|CODE)$/.test(n.nodeName))return;
  if(n.placeholder){var p=n.getAttribute("data-ph")||n.placeholder;n.setAttribute("data-ph",p);n.placeholder=side(p);}
  n.childNodes.forEach(walk);}
 function apply(){document.documentElement.lang=L;walk(document.body);
  document.querySelectorAll("[data-l]").forEach(function(b){b.setAttribute("aria-pressed",b.getAttribute("data-l")===L)});}
 document.addEventListener("click",function(e){var b=e.target.closest&&e.target.closest("[data-l]");if(!b)return;e.preventDefault();
  L=b.getAttribute("data-l");try{localStorage.setItem("cq-lang",L)}catch(x){}apply();});
 apply();})();
</script>"""
LANGCSS = """.lang{display:inline-flex;gap:2px;padding:3px;border-radius:999px;background:var(--glass);border:1px solid var(--edge)}
.lang button{border:0;background:none;color:var(--ink);font:700 13px/1 inherit;min-width:40px;min-height:32px;border-radius:999px;cursor:pointer;padding:0}
.lang button[aria-pressed="true"]{background:#fff;box-shadow:0 2px 6px rgba(0,40,80,.15)}
html[lang=en] .es,html[lang=es] .en:not([lang]){display:none}
"""

ADMIN_SHELL = """<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cacique Diario</title><style>""" + STYLE + LANGCSS + """
body{padding:16px}.wrap{max-width:980px;margin:0 auto}
header{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;color:#fff;text-shadow:0 2px 6px rgba(0,40,80,.35)}
header h1{margin:8px 0;font-size:28px}header a{color:#fff}.hr{display:flex;gap:12px;align-items:center}
nav{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 16px}
nav a{padding:9px 14px;border-radius:999px;background:var(--glass);border:1px solid var(--edge);color:var(--ink);text-decoration:none;font-size:15px}
nav a.on{background:#fff;font-weight:600}
section{background:var(--glass);border:1px solid var(--edge);border-radius:24px;padding:20px;backdrop-filter:blur(12px)}
h2{margin:0 0 6px}.sub{color:var(--sub);margin:0 0 14px}.empty{font-size:18px}
.item{background:rgba(255,255,255,.7);border-radius:16px;padding:14px;margin:12px 0;display:flex;flex-direction:column;gap:8px}
.item.new{border:2px dashed rgba(13,59,92,.25)}.meta{color:var(--sub);font-size:14px}
label{display:flex;flex-direction:column;gap:4px;font-size:14px;color:var(--sub)}label.inline{flex-direction:row;align-items:center;gap:8px}
input,textarea,select{font:inherit;font-size:16px;padding:9px 11px;border-radius:10px;border:1px solid #b9d3e6;background:#fff;color:var(--ink);width:100%}
input[type=checkbox]{width:auto}.checks{display:flex;flex-wrap:wrap;gap:6px 14px;align-items:center;font-size:15px}
.checks label{flex-direction:row;align-items:center;gap:5px;color:var(--ink)}.checks span{color:var(--sub);font-size:14px}
.row{display:flex;gap:8px;flex-wrap:wrap}
button{font:inherit;font-size:15px;padding:9px 16px;border-radius:999px;border:1px solid #fff;cursor:pointer;
 background:linear-gradient(#fff,#dcecf7);color:var(--ink)}button.ok{background:linear-gradient(#5fd38d,#1e8a4c);color:#fff}
button.no{background:linear-gradient(#f0857b,#b3392f);color:#fff}
.note{background:#fff;border-radius:12px;padding:10px 14px;margin-bottom:12px;border-left:5px solid var(--ok)}
.lnk{font-size:14px;font-weight:400;margin-left:8px}.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px}
.cards img{width:100%;border-radius:12px;box-shadow:0 6px 20px rgba(0,40,80,.2)}code{background:#fff;padding:1px 6px;border-radius:6px}
ul{padding-left:20px}li{margin:6px 0}li span{color:var(--sub);font-style:italic}
</style></head><body><div class="wrap"><header><h1>Cacique Diario</h1><div class="hr"><div class="lang"><button type="button" data-l="es">ES</button><button type="button" data-l="en">EN</button></div>
<a href="/admin/salir">Salir · Log out</a></div></header>
<nav>{{NAV}}</nav><section>{{BODY}}</section></div>""" + LANGJS + """</body></html>"""

LOGIN = """<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cacique Diario</title><style>""" + STYLE + LANGCSS + """
body{display:flex;align-items:center;justify-content:center;padding:16px}
form{background:var(--glass);border:1px solid var(--edge);border-radius:24px;padding:28px;width:100%;max-width:380px;backdrop-filter:blur(12px);
 display:flex;flex-direction:column;gap:12px}h1{margin:0}p{margin:0;color:var(--sub)}
input{font:inherit;font-size:17px;padding:11px;border-radius:12px;border:1px solid #b9d3e6}
button{font:inherit;font-size:17px;padding:11px;border-radius:999px;border:0;background:linear-gradient(#5fd38d,#1e8a4c);color:#fff;cursor:pointer}
.err{color:#b3392f}</style></head><body><form method="post" action="/admin/entrar"><h1>Cacique Diario</h1>
<p>Página de los adultos · Adults' page</p>{{ERR}}<input type="password" name="pw" placeholder="Contraseña · Password" autofocus required>
<button>Entrar · Log in</button><div class="lang" style="align-self:center"><button type="button" data-l="es">ES</button><button type="button" data-l="en">EN</button></div></form>""" + LANGJS + """</body></html>"""


# ================================================================ web server
class Handler(BaseHTTPRequestHandler):
    server_version = "CaciqueDiario"

    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="text/html; charset=utf-8", headers=None):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def jsend(self, obj):
        self.send(200, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8",
                  {"Access-Control-Allow-Origin": "*"})

    def go(self, where, cookie=None):
        h = {"Location": where}
        if cookie:
            h["Set-Cookie"] = cookie
        self.send(303, "", headers=h)

    def session(self):
        for part in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == "cd":
                with LOCK:
                    exp = SESSIONS.get(v)
                if exp and exp > time.time():
                    return v
        return None

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = dict(urllib.parse.parse_qsl(u.query))
        try:
            if u.path == "/health":
                return self.send(200, "ok", "text/plain")
            if u.path == "/":
                return self.send(200, SHOW.replace("%TEMAS%", json.dumps({k: list(v) for k, v in TEMAS.items()}, ensure_ascii=False)))
            if u.path == "/api/hoy":
                pid = q.get("para", "familia")
                ps = people()
                if pid not in ps:
                    pid = "familia"
                return self.jsend({"fecha": dt.date.today().isoformat(), "para": pid, "nombre": ps[pid].get("nombre", "") if pid != "familia" else "",
                                   "idioma": ps[pid].get("idioma", "es"), "mensajes": pick(pid, dt.date.today())})
            if u.path == "/api/mensaje":     # one message, for CaciqueHome to say out loud
                pid = q.get("para", "familia")
                pid = pid if pid in people() else "familia"
                msgs = [m for m in pick(pid, dt.date.today()) if not q.get("tema") or m["tema"] == q["tema"]] or pick(pid, dt.date.today())
                m = msgs[dt.datetime.now().hour % len(msgs)] if msgs else {"es": "", "en": ""}
                text = m.get("en") if q.get("idioma") == "en" else m.get("es")
                return self.jsend(dict(m, texto=text or ""))
            if u.path.startswith("/tarjeta/"):
                parts = u.path.split("/")
                if len(parts) == 4 and re.fullmatch(r"\d{4}-\d\d-\d\d", parts[2]) and re.fullmatch(r"[\w.-]+\.jpg", parts[3]):
                    f = path("imagenes", parts[2], parts[3])
                    if os.path.isfile(f):
                        return self.send(200, open(f, "rb").read(), "image/jpeg")
                return self.send(404, "not found", "text/plain")
            if u.path == "/admin":
                if not PASSWORD:
                    return self.send(503, "Run diario/setup-diario.sh first (no password yet).", "text/plain")
                if not self.session():
                    return self.send(200, LOGIN.replace("{{ERR}}", ""))
                return self.send(200, admin_page(q.get("t", "pendientes"), q.get("m", "")))
            if u.path == "/admin/salir":
                tok = self.session()
                if tok:
                    with LOCK:
                        SESSIONS.pop(tok, None)
                return self.go("/admin", "cd=; Path=/; Max-Age=0")
            return self.send(404, "not found", "text/plain")
        except Exception as e:
            print("  ! GET %s: %s" % (u.path, e), file=sys.stderr, flush=True)
            return self.send(500, "error: %s" % esc(e), "text/plain")

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        n = min(int(self.headers.get("Content-Length") or 0), 200000)
        form = urllib.parse.parse_qs(self.rfile.read(n).decode("utf-8", "replace"))
        f = {k: v[0] for k, v in form.items()}
        try:
            if u.path == "/admin/entrar":
                time.sleep(0.5)
                if PASSWORD and hmac.compare_digest(f.get("pw", "").encode(), PASSWORD.encode()):
                    tok = secrets.token_urlsafe(24)
                    with LOCK:
                        SESSIONS[tok] = time.time() + 12 * 3600
                    return self.go("/admin", "cd=%s; Path=/; HttpOnly; SameSite=Strict; Max-Age=43200" % tok)
                return self.send(200, LOGIN.replace("{{ERR}}", "<p class='err'>Contraseña incorrecta · Wrong password</p>"))
            if not self.session():
                return self.go("/admin")
            if (self.headers.get("Origin") or "").split("://")[-1] not in ("", self.headers.get("Host", "")):
                return self.send(403, "forbidden", "text/plain")      # only forms from this same page
            if u.path == "/admin/decidir":
                iid, d = f.get("id", ""), f.get("d")
                queue = load("cola.json", [])
                from_ai = next((x for x in queue if x["id"] == iid), None)
                if from_ai:
                    save("cola.json", [x for x in queue if x["id"] != iid])
                    if d == "ok":
                        own = load("propios.json", [])
                        own.append(dict(from_ai, es=f.get("es", from_ai["es"]).strip(), en=f.get("en", "").strip(), verificar=False))
                        save("propios.json", own)
                else:
                    dec = load("decisiones.json", {})
                    dec[iid] = "ok" if d == "ok" else "no"
                    save("decisiones.json", dec)
                    orig = next((x for x in library() if x["id"] == iid), None)
                    if d == "ok" and orig and (f.get("es", "").strip() != orig["es"] or f.get("en", "").strip() != orig.get("en", "")):
                        ed = load("ediciones.json", {})
                        ed[iid] = {"es": f.get("es", "").strip(), "en": f.get("en", "").strip()}
                        save("ediciones.json", ed)
                return self.go("/admin?t=pendientes&m=" + urllib.parse.quote("Aprobado · Approved" if d == "ok" else "Rechazado · Rejected"))
            if u.path == "/admin/persona":
                ps = load("personas.json", {})
                pid = f.get("id") or slug(f.get("nombre", ""))
                if not pid:
                    return self.go("/admin?t=personas")
                if f.get("borrar") and pid != "familia":
                    ps.pop(pid, None)
                else:
                    p = ps.get(pid, people().get(pid, {}))
                    p["nombre"] = f.get("nombre", p.get("nombre", pid)).strip() or pid
                    if "id" in f:                          # editing (a new person keeps the defaults)
                        p["roles"] = [r for r in form.get("roles", []) if r in ROLES] if pid != "familia" else []
                        p["temas"] = [t for t in form.get("temas", []) if t in TEMAS] or list(TEMAS)
                        p["por_dia"] = max(1, min(8, int(f.get("por_dia") or 3)))
                        p["idioma"] = f.get("idioma") if f.get("idioma") in ("es", "en", "es+en") else "es"
                    else:
                        p.setdefault("roles", ["adultos"]); p.setdefault("temas", list(TEMAS)); p.setdefault("idioma", "es")
                    ps[pid] = p
                save("personas.json", ps)
                today = os.path.join("dias", dt.date.today().isoformat() + ".json")
                c = load(today, {})
                c.pop(pid, None)
                os.makedirs(path("dias"), exist_ok=True)
                save(today, c)
                return self.go("/admin?t=personas&m=" + urllib.parse.quote("Guardado · Saved"))
            if u.path == "/admin/recordatorio":
                rs = load("recordatorios.json", [])
                if f.get("borrar"):
                    i = int(f.get("i", -1))
                    if 0 <= i < len(rs):
                        rs.pop(i)
                elif f.get("es", "").strip():
                    rs.append({"dias": sorted({int(x) for x in form.get("dias", []) if x.isdigit() and int(x) < 7}),
                               "es": f["es"].strip(), "en": f.get("en", "").strip(), "para": f.get("para", "todos"), "activo": True})
                save("recordatorios.json", rs)
                os.makedirs(path("dias"), exist_ok=True)
                save(os.path.join("dias", dt.date.today().isoformat() + ".json"), {})   # today's screens pick it up
                return self.go("/admin?t=recordatorios&m=" + urllib.parse.quote("Guardado · Saved"))
            if u.path == "/admin/propio":
                own = load("propios.json", [])
                if f.get("borrar"):
                    own = [x for x in own if x["id"] != f["borrar"]]
                elif f.get("es", "").strip():
                    own.append({"id": "propio-%s" % uuid.uuid4().hex[:8], "tema": f.get("tema") if f.get("tema") in TEMAS else "animo",
                                "es": f["es"].strip(), "en": f.get("en", "").strip(), "para": f.get("para", "todos"),
                                "fuente": f.get("fuente", "").strip() or "Cacique"})
                save("propios.json", own)
                return self.go("/admin?t=propios&m=" + urllib.parse.quote("Guardado · Saved"))
            if u.path == "/admin/ajustes":
                s = load("ajustes.json", {})
                if f.get("immich_key", "").strip():
                    s["immich_key"] = f["immich_key"].strip()
                for k in ("immich_url", "albumes_extra", "fondos"):
                    s[k] = f.get(k, "").strip()
                s["immich_url"] = s["immich_url"] or DEFAULT_SETTINGS["immich_url"]
                if not at_home(s["immich_url"]):          # privacy: the cards never go outside the house
                    s["immich_url"] = DEFAULT_SETTINGS["immich_url"]
                for k, lo, hi in (("por_dia", 1, 6), ("hora", 0, 23), ("guardar_dias", 1, 60)):
                    try:
                        s[k] = max(lo, min(hi, int(f.get(k))))
                    except (TypeError, ValueError):
                        pass
                s["ia"] = f.get("ia") == "1"
                save("ajustes.json", s)
                note = "Guardado · Saved"
                if s.get("immich_key"):
                    try:
                        album_id(ALBUM)
                        note += "\nCaciquePhotos OK: álbum \"%s\" listo · album ready" % ALBUM
                    except Exception as e:
                        note += "\nCaciquePhotos no respondió · did not answer: %s" % e
                return self.go("/admin?t=ajustes&m=" + urllib.parse.quote(note))
            if u.path == "/admin/presencia":
                st = load("ajustes.json", {})
                st["presencia"] = f.get("on") == "1"
                save("ajustes.json", st)
                return self.go("/admin?t=equipos&m=" + urllib.parse.quote("Guardado · Saved"))
            if u.path == "/admin/equipo":
                mac = f.get("mac", "").lower()
                if re.fullmatch(r"[0-9a-f:]{17}", mac):
                    names = load_secret("equipos", {})
                    names[mac] = {"nombre": f.get("nombre", "").strip()[:60], "persona": f.get("persona", "") if f.get("persona", "") in people() else ""}
                    save_secret("equipos", names)
                return self.go("/admin?t=equipos&m=" + urllib.parse.quote("Guardado · Saved"))
            if u.path == "/admin/rehacer":
                log = run_day(dt.date.today(), force=True)
                return self.go("/admin?t=hoy&m=" + urllib.parse.quote("\n".join(log.get("notas", []))))
            return self.send(404, "not found", "text/plain")
        except Exception as e:
            print("  ! POST %s: %s" % (u.path, e), file=sys.stderr, flush=True)
            return self.send(500, "error: %s" % esc(e), "text/plain")


def first_run():
    """Starting files for a new home (only written when they don't exist yet)."""
    os.makedirs(DATA, exist_ok=True)
    os.chmod(DATA, 0o700)                         # only this user can open the folder
    if not os.path.exists(path("personas.json")):
        save("personas.json", {"familia": {"nombre": "Familia", "roles": [], "temas": list(TEMAS), "idioma": "es"}})
    if not os.path.exists(path("recordatorios.json")):
        save("recordatorios.json", [{"dias": [2], "es": "Hoy es miércoles: saquemos la basura.",
                                     "en": "It's Wednesday: let's take out the trash.", "para": "todos", "activo": True}])
    if not os.path.exists(path("ajustes.json")):
        save("ajustes.json", dict(DEFAULT_SETTINGS))


def main():
    first_run()
    if "--probar" in sys.argv:
        day = dt.date.today()
        for pid, p in people().items():
            print("\n  %s:" % p.get("nombre", pid))
            for m in pick(pid, day, write=False):
                print("   - [%s] %s" % (m["tema"], m["es"]))
        print("\n  Por aprobar · waiting for approval: %d" % (
            sum(1 for it in library() if status_of(it) == "pendiente") + len(load("cola.json", []))))
        return
    if "--hoy" in sys.argv:
        log = run_day(dt.date.today(), force=True)
        print("  Hecho · Done:", " · ".join(log.get("notas", [])))
        return
    threading.Thread(target=scheduler, daemon=True).start()
    threading.Thread(target=presence_loop, daemon=True).start()
    srv = ThreadingHTTPServer((BIND, PORT), Handler)
    print("  Cacique Diario on port %d (data: %s)" % (PORT, DATA), flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
