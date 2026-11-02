#!/usr/bin/env python3
"""
ElCaciqueDeck Field Manual builder.

Turns manual/src/*.md (each with a Spanish and an English half) into:
  manual/site/                      plain web pages (open index.html in any browser)
  manual/dist/elcaciquedeck-manual.zim   a Kiwix book for CaciqueLibrary

Run (on a computer with Python 3):
  pip install libzim markdown
  python3 manual/build_manual.py

The ThinkPad doesn't need to run this: the finished .zim is in the repo and
tools/update.sh copies it into Library/Kiwix.
"""
import datetime
import html
import pathlib
import re
import struct
import zlib

import markdown

ROOT = pathlib.Path(__file__).resolve().parent
SRC, SITE, DIST = ROOT / "src", ROOT / "site", ROOT / "dist"
ZIM_NAME = "elcaciquedeck-manual"

CSS = """
:root{--bg:#0b0b0d;--card:#141417;--line:#2c2c30;--txt:#f1ece2;--muted:#9a9488;--amber:#ffb35c;--glow:#ff8a1c}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--txt);font:16px/1.6 "DejaVu Sans",system-ui,sans-serif}
main{max-width:880px;margin:0 auto;padding:20px 16px 60px}
header.top{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;
  max-width:880px;margin:0 auto;padding:16px 16px 0}
.brand{font-style:italic;font-weight:800;letter-spacing:.12em;color:var(--amber);text-shadow:0 0 10px var(--glow);text-decoration:none}
.lang{display:flex;gap:6px}
.lang button{background:var(--card);color:var(--muted);border:1px solid var(--line);border-radius:6px;padding:6px 10px;font:inherit;font-size:13px;cursor:pointer}
.lang button[aria-pressed=true]{color:#1a1206;background:var(--amber);border-color:var(--amber)}
h1{color:var(--amber);text-shadow:0 0 10px rgba(255,138,28,.45);font-size:clamp(24px,5vw,34px);margin:.6em 0 .3em}
h2{color:var(--amber);border-bottom:1px solid var(--line);padding-bottom:4px;margin-top:1.6em}
h3{color:#ffd29a;margin-top:1.3em}
a{color:var(--amber)}
code{background:#1c1c21;border:1px solid var(--line);border-radius:4px;padding:1px 5px;font-family:"DejaVu Sans Mono",monospace;font-size:.92em}
pre{background:#101013;border:1px solid var(--line);border-left:3px solid var(--amber);border-radius:6px;padding:12px;overflow-x:auto}
pre code{background:none;border:0;padding:0;font-size:15px}
table{border-collapse:collapse;width:100%;margin:12px 0;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top}
th{background:#1a1a1e;color:var(--amber)}
.langblock{border:1px solid var(--line);border-radius:10px;padding:4px 16px 12px;margin:16px 0;background:var(--card)}
.langtag{display:inline-block;margin-top:10px;font-size:12px;letter-spacing:.2em;color:var(--muted)}
body.only-es .en, body.only-en .es{display:none}
nav.pager{display:flex;justify-content:space-between;gap:10px;margin-top:30px}
nav.pager a{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 14px;text-decoration:none}
ul.toc{list-style:none;padding:0;display:grid;gap:10px}
ul.toc a{display:flex;gap:12px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;text-decoration:none}
ul.toc a:hover{border-color:var(--glow);box-shadow:0 0 12px rgba(255,138,28,.3)}
.toc .ico{font-size:24px}.toc .t2{display:block;color:var(--muted);font-size:13px}
.foot{color:var(--muted);font-size:12px;text-align:center;margin-top:40px}
"""

JS = """
(function(){
  var modes=['both','es','en'];
  function apply(m){
    document.body.className = m==='both' ? '' : 'only-'+m;
    document.querySelectorAll('.lang button').forEach(function(b){b.setAttribute('aria-pressed', b.dataset.m===m);});
    try{localStorage.setItem('manual-lang',m);}catch(e){}
  }
  var m='both'; try{m=localStorage.getItem('manual-lang')||'both';}catch(e){}
  if(modes.indexOf(m)<0)m='both';
  document.querySelectorAll('.lang button').forEach(function(b){b.onclick=function(){apply(b.dataset.m);};});
  apply(m);
})();
"""


def parse(path):
    text = path.read_text(encoding="utf-8")
    meta = {}
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
        text = text[m.end():]
    es, _, en = text.partition("<!-- EN -->")
    es = es.replace("<!-- ES -->", "").strip()
    return meta, es, en.strip()


def md(text):
    return markdown.markdown(text, extensions=["tables", "fenced_code"])


def page(title, body, rel=""):
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="{rel}manual.css"></head>
<body>
<header class="top"><a class="brand" href="{rel}index.html">ELCACIQUEDECK · MANUAL</a>
<div class="lang" role="group" aria-label="Idioma / Language">
<button data-m="es">Español</button><button data-m="en">English</button><button data-m="both">Ambos</button></div></header>
<main>{body}</main>
<script src="{rel}manual.js"></script></body></html>"""


def png_icon(size=48):
    """A small amber-on-black 'C' badge, drawn pixel by pixel (no image libraries needed)."""
    rows = []
    c = (size - 1) / 2
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            d = ((x - c) ** 2 + (y - c) ** 2) ** 0.5
            ang_open = (x > c) and abs(y - c) < size * 0.16
            if d > size / 2:
                px = (11, 11, 13, 0)
            elif size * 0.26 < d < size * 0.40 and not ang_open:
                px = (255, 179, 92, 255)
            else:
                px = (20, 20, 23, 255)
            row += bytes(px)
        rows.append(bytes(row))
    raw = zlib.compress(b"".join(rows), 9)

    def chunk(t, data):
        return struct.pack(">I", len(data)) + t + data + struct.pack(">I", zlib.crc32(t + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", raw) + chunk(b"IEND", b""))


def build_site():
    SITE.mkdir(parents=True, exist_ok=True)
    chapters = []
    for p in sorted(SRC.glob("*.md")):
        meta, es, en = parse(p)
        chapters.append((p.stem, meta, es, en))

    for i, (slug, meta, es, en) in enumerate(chapters):
        prev = chapters[i - 1] if i > 0 else None
        nxt = chapters[i + 1] if i + 1 < len(chapters) else None
        pager = '<nav class="pager">'
        pager += f'<a href="{prev[0]}.html">← {html.escape(prev[1]["title_es"])}</a>' if prev else '<a href="index.html">← Índice · Index</a>'
        pager += f'<a href="{nxt[0]}.html">{html.escape(nxt[1]["title_es"])} →</a>' if nxt else '<a href="index.html">Índice · Index →</a>'
        pager += "</nav>"
        body = (f'<h1>{meta.get("icon","")} {html.escape(meta["title_es"])} · {html.escape(meta["title_en"])}</h1>'
                f'<section class="langblock es"><span class="langtag">ESPAÑOL</span>{md(es)}</section>'
                f'<section class="langblock en"><span class="langtag">ENGLISH</span>{md(en)}</section>{pager}')
        (SITE / f"{slug}.html").write_text(page(f'{meta["title_es"]} · {meta["title_en"]}', body), encoding="utf-8")

    toc = "".join(
        f'<li><a href="{slug}.html"><span class="ico">{meta.get("icon","")}</span>'
        f'<span>{html.escape(meta["title_es"])}<span class="t2">{html.escape(meta["title_en"])}</span></span></a></li>'
        for slug, meta, _, _ in chapters)
    intro = ("<h1>Manual de Campo · Field Manual</h1>"
             '<section class="langblock es"><span class="langtag">ESPAÑOL</span><p>Cómo encender, cuidar, diagnosticar y '
             "arreglar el Home Lab ElCaciqueDeck <b>sin depender de nadie</b>, ni siquiera de la inteligencia artificial. "
             "Escrito para quien no es programador, a partir de los problemas reales que resolvimos.</p></section>"
             '<section class="langblock en"><span class="langtag">ENGLISH</span><p>How to start, care for, diagnose and fix '
             "the ElCaciqueDeck Home Lab <b>without depending on anyone</b>, not even AI. Written for non-programmers, "
             "from the real problems we solved.</p></section>"
             f'<ul class="toc">{toc}</ul>'
             f'<p class="foot">Hecho en Puerto Rico 🇵🇷 · Solo para aprendizaje / For learning purposes only · '
             f'{datetime.date.today().isoformat()}</p>')
    (SITE / "index.html").write_text(page("Manual de Campo · Field Manual", intro), encoding="utf-8")
    (SITE / "manual.css").write_text(CSS, encoding="utf-8")
    (SITE / "manual.js").write_text(JS, encoding="utf-8")
    return chapters


def build_zim(chapters):
    from libzim.writer import Creator, FileProvider, Hint, Item, StringProvider

    class FileItem(Item):
        def __init__(self, path, title, mimetype):
            super().__init__()
            self.path, self.title, self.mimetype = path, title, mimetype

        def get_path(self): return self.path
        def get_title(self): return self.title
        def get_mimetype(self): return self.mimetype
        def get_contentprovider(self): return FileProvider(str(SITE / self.path))
        def get_hints(self): return {Hint.FRONT_ARTICLE: self.mimetype == "text/html"}

    DIST.mkdir(parents=True, exist_ok=True)
    out = DIST / f"{ZIM_NAME}.zim"
    if out.exists():
        out.unlink()
    titles = {f"{s}.html": f'{m["title_es"]} · {m["title_en"]}' for s, m, _, _ in chapters}
    titles["index.html"] = "Manual de Campo · Field Manual"
    mimes = {".html": "text/html", ".css": "text/css", ".js": "application/javascript"}
    with Creator(str(out)).config_indexing(True, "spa") as c:
        c.set_mainpath("index.html")
        try:
            c.add_illustration(png_icon(48), 48)      # libzim 4.x
        except TypeError:
            c.add_illustration(48, png_icon(48))      # libzim 3.x
        for k, v in {
            "Name": ZIM_NAME, "Title": "ElCaciqueDeck · Manual de Campo",
            "Description": "Manual bilingüe para cuidar el Home Lab / Bilingual Home Lab field manual",
            "LongDescription": "Cómo encender, cuidar, diagnosticar y arreglar el Home Lab ElCaciqueDeck. "
                               "How to start, care for, diagnose and fix the ElCaciqueDeck Home Lab.",
            "Language": "spa,eng", "Creator": "ElCaciqueDeck", "Publisher": "ElCaciqueDeck",
            "Date": datetime.date.today().isoformat(), "Tags": "homelab;manual;bilingual",
        }.items():
            c.add_metadata(k, v)
        for f in sorted(SITE.iterdir()):
            c.add_item(FileItem(f.name, titles.get(f.name, f.name), mimes.get(f.suffix, "application/octet-stream")))
    return out


if __name__ == "__main__":
    ch = build_site()
    z = build_zim(ch)
    print(f"Built {len(ch)} chapters -> {SITE}  and  {z} ({z.stat().st_size//1024} KB)")
