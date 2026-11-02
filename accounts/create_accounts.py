#!/usr/bin/env python3
"""
ElCaciqueDeck - create the family's accounts in every Cacique app.

Run it with:  bash ~/elcaciquedeck/accounts/create-accounts.sh
(that wrapper also turns on the Arcade's no-login mode and refreshes the front page).

Who gets what (people list: ~/elcaciquedeck-data/accounts/people.txt, see people.sh):

  app            El Cacique (admin)   adults            Familia (family)         Invitado (guest)
  CaciqueFlix    admin, hidden        own profile       no password, up to PG    no password, up to PG-13
  CaciquePhotos  admin                own private lib   "Familia Abierta" slideshow link (no login)
  CaciqueDocs    superuser            own private docs  -                        -
  CaciqueArcade  admin                own login         open to play (no login, "kiosk" mode)
  CaciqueHome    admin                regular user      -                        -
  CaciqueVault   invited              invited           -                        -

Safe to run again: it never deletes anything, never resets a password that already exists,
and never removes admin rights from anyone (you do that by hand when you're ready).
Starter passwords are saved ONLY on this laptop (~/elcaciquedeck-data/accounts, private folder)
until you save them in CaciqueVault and run:  bash ~/elcaciquedeck/accounts/people.sh forget-passwords
Only the Python that comes with Ubuntu is needed.
"""
import base64, getpass, http.client as httpclient, json, os, re, secrets, socket, struct, subprocess, sys, urllib.parse

HOME = os.path.expanduser("~")
ACC = os.environ.get("ACCOUNTS_DIR") or os.path.join(HOME, "elcaciquedeck-data", "accounts")
HOST = os.environ.get("CACIQUE_HOST", "127.0.0.1")       # the apps run on this same laptop
PORTS = {"jellyfin": 8096, "immich": 2283, "paperless": 8000, "romm": 8090, "homeassistant": 8123, "vaultwarden": 8222}
NAMES = {"jellyfin": "CaciqueFlix", "immich": "CaciquePhotos", "paperless": "CaciqueDocs", "romm": "CaciqueArcade",
         "homeassistant": "CaciqueHome", "vaultwarden": "CaciqueVault"}
EMAIL_DOMAIN = "cacique.home"
ALBUM_NAME = "Familia Abierta · Family Open"
ALBUM_SLUG = "familia-abierta"
JF_RATING = {"family": 10, "guest": 13}                     # Jellyfin US scores: PG = 10, PG-13 = 13

WORDS = ("Coqui Yunque Flamboyan Mofongo Guayaba Quenepa Ceiba Tostones Alcapurria Coco Mango Parcha Acerola "
         "Guanabana Tembleque Pastelillo Bacalaito Malecon Playa Cordillera Bohio Batey Areyto Guiro Cuatro Maraca "
         "Plena Bomba Salsa Cometa Faro Palma Arena Ola Brisa Lluvia Trueno Montana Rio Cascada Cueva Sol Luna "
         "Estrella Colibri Guaraguao Pelicano Iguana Tortuga Delfin Ballena Manati Cotorra Juey Chiringa Trompo "
         "Gallito Canica Yuca Platano Batata Calabaza Aguacate").split()

report = []          # (app, person, result)


def say(msg=""):
    print(msg, flush=True)


def note(app, who, result):
    report.append((app, who, result))
    say("  %-14s %-12s %s" % (NAMES.get(app, app), who, result))


# ---------------------------------------------------------------- small helpers
def laptop_ip():
    try:
        out = subprocess.run(["ip", "route", "get", "1.1.1.1"], capture_output=True, text=True, timeout=5).stdout
        m = re.search(r"\bsrc (\S+)", out)
        if m:
            return m.group(1)
    except Exception:
        pass
    return "<laptop number>"


def friendly_password():
    return "-".join(secrets.choice(WORDS) for _ in range(3)) + "-%02d" % secrets.randbelow(100)


def strong_password():
    return secrets.token_urlsafe(18)


def call(port, method, path, body=None, headers=None, form=None, timeout=20):
    """One web request to an app on this laptop. Returns (status, headers, data). Never follows redirects."""
    h = {"Accept": "application/json"}
    h.update(headers or {})
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        h["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    conn = httpclient.HTTPConnection(HOST, port, timeout=timeout)
    try:
        conn.request(method, path, body=data, headers=h)
        r = conn.getresponse()
        raw = r.read()
        hdrs = {}
        for k, v in r.getheaders():
            hdrs.setdefault(k.lower(), []).append(v)
        try:
            out = json.loads(raw.decode() or "null")
        except Exception:
            out = raw.decode(errors="replace")
        return r.status, hdrs, out
    finally:
        conn.close()


def is_up(port):
    try:
        socket.create_connection((HOST, port), timeout=3).close()
        return True
    except Exception:
        return False


def short(x, n=160):
    s = x if isinstance(x, str) else json.dumps(x)
    return s.replace("\n", " ")[:n]


def ask_login(app, what="admin user name"):
    say("")
    say("  %s: type the %s you use today (or just press Enter to skip %s)" % (NAMES[app], what, NAMES[app]))
    try:
        user = input("    %s: " % what).strip()
    except EOFError:
        return None
    if not user:
        return None
    pw = getpass.getpass("    password (it won't show while you type): ")
    return user, pw


# ---------------------------------------------------------------- people + passwords
def load_people():
    path = os.path.join(ACC, "people.txt")
    if not os.path.exists(path):
        sys.exit("  No people list yet. Add people first:  bash ~/elcaciquedeck/accounts/people.sh add <login> <nickname>")
    people = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) != 3 or parts[2] not in ("admin", "adult", "family", "guest"):
            say("  [WARN] Skipping a line I don't understand in people.txt: %s" % line)
            continue
        people.append({"login": parts[0], "nick": parts[1], "type": parts[2],
                       "email": "%s@%s" % (parts[0], EMAIL_DOMAIN)})
    return people


def load_passwords(people):
    path = os.path.join(ACC, "passwords.json")
    try:
        pw = json.load(open(path))
    except Exception:
        pw = {}
    pw.setdefault("people", {})
    pw.setdefault("elcacique", {})
    for p in people:
        if p["type"] == "adult":
            pw["people"].setdefault(p["login"], friendly_password())
    for app in ("jellyfin", "immich", "paperless", "romm", "homeassistant"):
        pw["elcacique"].setdefault(app, strong_password())
    save_json(path, pw)
    return pw


def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)


def ask_owner(app, ident, people, pw):
    """The admin account used today is often someone's own personal account: link it, so we don't make a second one."""
    links = pw.setdefault("links", {}).setdefault(app, {})
    if ident.lower() in (v.lower() for v in links.values()):
        return
    adults = [p["login"] for p in people if p["type"] == "adult"]
    if not adults:
        return
    say("    Is \"%s\" someone's own personal account? Type their login (%s)" % (ident, ", ".join(adults)))
    try:
        ans = input("    or just press Enter if it's only an admin account: ").strip().lower()
    except EOFError:
        ans = ""
    if ans in adults:
        links[ans] = ident
        save_json(os.path.join(ACC, "passwords.json"), pw)
        say("    OK: \"%s\" is %s's account (it stays as it is; no second account is made)." % (ident, ans))


def linked(pw, app, login):
    return pw.get("links", {}).get(app, {}).get(login)


def password_for(p, app, pw):
    if p["type"] == "admin":
        return pw["elcacique"][app]
    if p["type"] == "adult":
        return pw["people"][p["login"]]
    return ""      # Familia / Invitado: no password


# ================================================================ CaciqueFlix (Jellyfin)
def jf_auth(token=None):
    a = 'MediaBrowser Client="ElCaciqueDeck", Device="accounts", DeviceId="elcaciquedeck-accounts", Version="1.0"'
    if token:
        a += ', Token="%s"' % token
    return {"Authorization": a, "X-Emby-Authorization": a}


def jf_login(user, password):
    st, _, d = call(PORTS["jellyfin"], "POST", "/Users/AuthenticateByName", {"Username": user, "Pw": password}, jf_auth())
    if st == 200 and isinstance(d, dict) and d.get("AccessToken"):
        if not d.get("User", {}).get("Policy", {}).get("IsAdministrator"):
            say("    That account is not an administrator in CaciqueFlix.")
            return None, None
        return d["AccessToken"], d["User"]["Id"]
    return None, None


def do_jellyfin(people, pw):
    app = "jellyfin"
    tok, me = jf_login("El Cacique", pw["elcacique"][app])
    while not tok:
        login = ask_login(app)
        if not login:
            note(app, "-", "skipped")
            return {}
        tok, me = jf_login(*login)
        if not tok:
            say("    Wrong name or password, try again.")
        else:
            ask_owner(app, login[0], people, pw)
    H = jf_auth(tok)
    st, _, users = call(PORTS[app], "GET", "/Users", headers=H)
    if st != 200:
        note(app, "-", "could not list users (%s)" % st)
        return {}
    by_name = {u["Name"].lower(): u for u in users}
    done = {}
    for p in people:
        name = linked(pw, app, p["login"]) or p["nick"]
        u = by_name.get(name.lower())
        if u:
            result = "already there (password not changed)"
        else:
            st, _, u = call(PORTS[app], "POST", "/Users/New", {"Name": name, "Password": password_for(p, app, pw)}, H)
            if st not in (200, 201) or not isinstance(u, dict):
                note(app, p["login"], "FAILED to create (%s %s)" % (st, short(u)))
                continue
            result = "created"
        uid = u["Id"]
        if uid == me and p["type"] != "admin":
            note(app, p["login"], result + " - this is the account you logged in with; left as it is")
            done[p["login"]] = (name, result.startswith("created"))
            continue
        st, _, full = call(PORTS[app], "GET", "/Users/%s" % uid, headers=H)
        pol = (full or {}).get("Policy") or {}
        if p["type"] == "admin":
            pol.update(IsAdministrator=True, IsHidden=True, IsDisabled=False, EnableAllFolders=True, MaxParentalRating=None)
        elif p["type"] == "adult":
            pol.update(IsHidden=False, IsDisabled=False, EnableAllFolders=True)
            if not pol.get("IsAdministrator"):
                pol.update(MaxParentalRating=None, BlockUnratedItems=[])
        else:
            pol.update(IsAdministrator=False, IsHidden=False, IsDisabled=False, EnableAllFolders=True,
                       MaxParentalRating=JF_RATING[p["type"]], MaxParentalSubRating=None,
                       BlockUnratedItems=["Movie", "Series", "Trailer"],
                       EnableContentDeletion=False, EnableUserPreferenceAccess=False, EnableRemoteAccess=False)
        st, _, d = call(PORTS[app], "POST", "/Users/%s/Policy" % uid, pol, H)
        if st not in (200, 204):
            result += " - settings NOT applied (%s %s)" % (st, short(d))
        elif p["type"] in JF_RATING:
            result += " - movies up to %s" % ("PG" if p["type"] == "family" else "PG-13")
        if p["type"] == "adult" and pol.get("IsAdministrator"):
            result += " - still an admin (remove it by hand when El Cacique works)"
        note(app, p["login"], result)
        done[p["login"]] = (name, result.startswith("created"))
    return done


# ================================================================ CaciquePhotos (Immich)
def im_login(email, password):
    st, _, d = call(PORTS["immich"], "POST", "/api/auth/login", {"email": email, "password": password})
    if st in (200, 201) and isinstance(d, dict) and d.get("accessToken"):
        return d["accessToken"], d
    return None, None


def do_immich(people, pw, ip):
    app = "immich"
    ec = next(p for p in people if p["type"] == "admin")
    tok, me = im_login(ec["email"], pw["elcacique"][app])
    while not tok:
        login = ask_login(app, "admin email")
        if not login:
            note(app, "-", "skipped")
            return {}
        tok, me = im_login(*login)
        if not tok:
            say("    Wrong email or password, try again.")
        elif not me.get("isAdmin"):
            say("    That account is not an administrator in CaciquePhotos.")
            tok = None
        else:
            ask_owner(app, login[0], people, pw)
    H = {"Authorization": "Bearer " + tok}
    st, _, users = call(PORTS[app], "GET", "/api/admin/users", headers=H)
    if st != 200:
        note(app, "-", "could not list users (%s %s)" % (st, short(users)))
        return {}
    by_email = {u["email"].lower(): u for u in users}
    done, adult_ids = {}, []
    for p in people:
        if p["type"] in ("family", "guest"):
            continue
        email = (linked(pw, app, p["login"]) or p["email"]).lower()
        u = by_email.get(email)
        created = not u
        if u:
            note(app, p["login"], "already there (password not changed)")
        else:
            st, _, u = call(PORTS[app], "POST", "/api/admin/users", {
                "email": p["email"], "name": p["nick"], "password": password_for(p, app, pw),
                "isAdmin": p["type"] == "admin", "shouldChangePassword": p["type"] == "adult"}, H)
            if st not in (200, 201):
                note(app, p["login"], "FAILED to create (%s %s)" % (st, short(u)))
                continue
            note(app, p["login"], "created" + (" (asks for a new password the first time)" if p["type"] == "adult" else ""))
        done[p["login"]] = (u.get("email", email), created)
        if p["type"] == "adult":
            adult_ids.append(u["id"])

    # the "Familia Abierta" album, owned by El Cacique, shown to visitors as a slideshow link
    etok, _ = im_login(ec["email"], pw["elcacique"][app])
    if not etok:
        note(app, "Familia Abierta", "skipped (could not log in as El Cacique)")
        return done
    E = {"Authorization": "Bearer " + etok}
    st, _, albums = call(PORTS[app], "GET", "/api/albums", headers=E)
    album = next((a for a in (albums if isinstance(albums, list) else []) if a.get("albumName") == ALBUM_NAME), None)
    if album:
        have = {au.get("user", {}).get("id") for au in album.get("albumUsers", [])}
        missing = [i for i in adult_ids if i not in have]
        if missing:
            call(PORTS[app], "PUT", "/api/albums/%s/users" % album["id"],
                 {"albumUsers": [{"userId": i, "role": "editor"} for i in missing]}, E)
        note(app, "Familia Abierta", "album already there (%d adults can add photos)" % len(adult_ids))
    else:
        st, _, album = call(PORTS[app], "POST", "/api/albums", {
            "albumName": ALBUM_NAME,
            "description": "Fotos para enseñar a las visitas · Photos we love to show guests",
            "albumUsers": [{"userId": i, "role": "editor"} for i in adult_ids]}, E)
        if st not in (200, 201):
            note(app, "Familia Abierta", "FAILED to create the album (%s %s)" % (st, short(album)))
            return done
        note(app, "Familia Abierta", "album created; every adult can add photos to it")
    st, _, links = call(PORTS[app], "GET", "/api/shared-links", headers=E)
    link = next((l for l in (links if isinstance(links, list) else [])
                 if (l.get("album") or {}).get("id") == album["id"]), None)
    if not link:
        body = {"type": "ALBUM", "albumId": album["id"], "slug": ALBUM_SLUG, "allowUpload": False,
                "allowDownload": False, "showMetadata": False,
                "description": "Familia Abierta · Family Open"}
        st, _, link = call(PORTS[app], "POST", "/api/shared-links", body, E)
        if st not in (200, 201):          # older Immich without custom link names
            body.pop("slug")
            st, _, link = call(PORTS[app], "POST", "/api/shared-links", body, E)
        if st not in (200, 201):
            note(app, "Familia Abierta", "FAILED to make the visitor link (%s %s)" % (st, short(link)))
            return done
    url = "http://%s:%d/%s" % (ip, PORTS[app], ("s/" + link["slug"]) if link.get("slug") else ("share/" + link["key"]))
    with open(os.path.join(ACC, "open-photos-link.txt"), "w") as f:
        f.write(url + "\n")
    note(app, "Familia Abierta", "visitor slideshow link: " + url)
    return done


# ================================================================ CaciqueDocs (Paperless)
PL_MODELS = ["document", "tag", "correspondent", "documenttype", "storagepath", "savedview", "note",
             "sharelink", "customfield"]
PL_PERMS = (["%s_%s" % (a, m) for m in PL_MODELS for a in ("add", "change", "delete", "view")]
            + ["add_uisettings", "change_uisettings", "view_uisettings", "view_paperlesstask",
               "view_user", "view_group"])


def pl_headers(user, password):
    return {"Authorization": "Basic " + base64.b64encode(("%s:%s" % (user, password)).encode()).decode()}


def pl_check(H):
    st, _, d = call(PORTS["paperless"], "GET", "/api/users/?page_size=1000", headers=H)
    return st == 200 and isinstance(d, dict) and "results" in d


def do_paperless(people, pw):
    app = "paperless"
    H = pl_headers("elcacique", pw["elcacique"][app])
    while not pl_check(H):
        login = ask_login(app)
        if not login:
            note(app, "-", "skipped")
            return {}
        H = pl_headers(*login)
        if not pl_check(H):
            say("    Wrong name or password (remember: capital letters matter), or not an admin. Try again.")
        else:
            ask_owner(app, login[0], people, pw)
    st, _, d = call(PORTS[app], "GET", "/api/users/?page_size=1000", headers=H)
    by_name = {u["username"].lower(): u for u in d["results"]}
    # the "Adultos" group: can upload and see their own documents, and share them
    st, _, g = call(PORTS[app], "GET", "/api/groups/?page_size=1000", headers=H)
    group = next((x for x in g.get("results", []) if x["name"] == "Adultos"), None) if isinstance(g, dict) else None
    if not group:
        perms = list(PL_PERMS)
        for _ in range(len(PL_PERMS)):
            st, _, group = call(PORTS[app], "POST", "/api/groups/", {"name": "Adultos", "permissions": perms}, H)
            if st in (200, 201):
                break
            bad = re.findall(r"codename=(\w+)", short(group, 5000))
            if not bad:
                break
            perms = [x for x in perms if x not in bad]    # this Paperless version doesn't have those
        if st not in (200, 201):
            note(app, "Adultos group", "FAILED (%s %s)" % (st, short(group)))
            group = None
        else:
            note(app, "Adultos group", "created (%d permissions)" % len(perms))
    done = {}
    for p in people:
        if p["type"] in ("family", "guest"):
            continue
        mine = linked(pw, app, p["login"]) or p["login"]
        if mine.lower() in by_name:
            note(app, p["login"], "already there (password not changed)")
            done[p["login"]] = (by_name[mine.lower()]["username"], False)
            continue
        admin = p["type"] == "admin"
        body = {"username": p["login"], "password": password_for(p, app, pw), "first_name": p["nick"],
                "email": p["email"], "is_staff": admin, "is_superuser": admin, "is_active": True,
                "groups": [] if admin or not group else [group["id"]]}
        st, _, u = call(PORTS[app], "POST", "/api/users/", body, H)
        if st in (200, 201):
            note(app, p["login"], "created" + (" (superuser)" if admin else " (own private documents)"))
            done[p["login"]] = (p["login"], True)
        else:
            note(app, p["login"], "FAILED to create (%s %s)" % (st, short(u)))
    return done


# ================================================================ CaciqueArcade (RomM)
def rm_token(user, password):
    st, _, d = call(PORTS["romm"], "POST", "/api/token", form={
        "grant_type": "password", "username": user, "password": password, "scope": "users.read users.write"})
    if st == 200 and isinstance(d, dict) and d.get("access_token"):
        return d["access_token"]
    return None


def do_romm(people, pw):
    app = "romm"
    tok = rm_token("elcacique", pw["elcacique"][app])
    while not tok:
        login = ask_login(app)
        if not login:
            note(app, "-", "skipped")
            return {}
        tok = rm_token(*login)
        if not tok:
            say("    Wrong name or password, or not an admin. Try again.")
        else:
            ask_owner(app, login[0], people, pw)
    H = {"Authorization": "Bearer " + tok}
    st, _, users = call(PORTS[app], "GET", "/api/users", headers=H)
    if st != 200 or not isinstance(users, list):
        note(app, "-", "could not list users (%s %s)" % (st, short(users)))
        return {}
    by_name = {u["username"].lower(): u for u in users}
    done = {}
    for p in people:
        if p["type"] in ("family", "guest"):
            continue
        mine = (linked(pw, app, p["login"]) or p["login"]).lower()
        if mine in by_name:
            note(app, p["login"], "already there (password not changed)")
            done[p["login"]] = (by_name[mine]["username"], False)
            continue
        fields = {"username": p["login"], "email": p["email"], "password": password_for(p, app, pw),
                  "role": "admin" if p["type"] == "admin" else "viewer"}
        st, _, u = call(PORTS[app], "POST", "/api/users", fields, H)
        if st == 422:       # older RomM took form fields
            st, _, u = call(PORTS[app], "POST", "/api/users", headers=H, form=fields)
        if st in (200, 201):
            note(app, p["login"], "created")
            done[p["login"]] = (p["login"], True)
        else:
            note(app, p["login"], "FAILED to create (%s %s)" % (st, short(u)))
    note(app, "familia/invitado", "play without logging in (kiosk mode, read-only)")
    return done


# ================================================================ CaciqueHome (Home Assistant)
class WebSocket:
    """Tiny websocket client (enough for Home Assistant's API), so nothing extra must be installed."""

    def __init__(self, host, port, path):
        self.s = socket.create_connection((host, port), timeout=20)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(("GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                        "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n" % (path, host, port, key)).encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.s.recv(1)
            if not chunk:
                raise ConnectionError("websocket closed during handshake")
            head += chunk
        if b" 101 " not in head.split(b"\r\n")[0]:
            raise ConnectionError("websocket refused: " + head.split(b"\r\n")[0].decode(errors="replace"))
        self.n = 0

    def _read(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.s.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("websocket closed")
            buf += chunk
        return buf

    def _frame(self, opcode, payload):
        mask = os.urandom(4)
        n = len(payload)
        if n < 126:
            head = struct.pack("!BB", 0x80 | opcode, 0x80 | n)
        elif n < 65536:
            head = struct.pack("!BBH", 0x80 | opcode, 0x80 | 126, n)
        else:
            head = struct.pack("!BBQ", 0x80 | opcode, 0x80 | 127, n)
        self.s.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def send(self, obj):
        self._frame(0x1, json.dumps(obj).encode())

    def recv(self):
        msg = b""
        while True:
            b1, b2 = self._read(2)
            fin, opcode, n = b1 & 0x80, b1 & 0x0F, b2 & 0x7F
            if n == 126:
                n = struct.unpack("!H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack("!Q", self._read(8))[0]
            mask = self._read(4) if b2 & 0x80 else None
            data = self._read(n)
            if mask:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            if opcode == 0x9:          # ping -> pong
                self._frame(0xA, data)
                continue
            if opcode == 0x8:
                raise ConnectionError("websocket closed by Home Assistant")
            msg += data
            if fin:
                return json.loads(msg.decode())

    def call(self, **cmd):
        self.n += 1
        cmd["id"] = self.n
        self.send(cmd)
        while True:
            m = self.recv()
            if m.get("id") == self.n and m.get("type") == "result":
                return m

    def close(self):
        try:
            self._frame(0x8, b"")
            self.s.close()
        except Exception:
            pass


def ha_token(user, password):
    port = PORTS["homeassistant"]
    cid = "http://%s:%d/" % (HOST, port)
    st, _, flow = call(port, "POST", "/auth/login_flow", {
        "client_id": cid, "handler": ["homeassistant", None], "redirect_uri": cid + "?auth_callback=1"})
    if st != 200 or not isinstance(flow, dict) or "flow_id" not in flow:
        return None, "login page answered %s" % st
    st, _, res = call(port, "POST", "/auth/login_flow/%s" % flow["flow_id"],
                      {"client_id": cid, "username": user, "password": password})
    if not isinstance(res, dict) or res.get("type") != "create_entry":
        if isinstance(res, dict) and res.get("step_id") == "mfa":
            return None, "that account uses a second step (MFA); use an admin without it"
        return None, "wrong name or password"
    st, _, t = call(port, "POST", "/auth/token", form={
        "grant_type": "authorization_code", "code": res["result"], "client_id": cid})
    if st == 200 and isinstance(t, dict) and t.get("access_token"):
        return t["access_token"], None
    return None, "token answered %s" % st


def do_homeassistant(people, pw):
    app = "homeassistant"
    tok, why = ha_token("elcacique", pw["elcacique"][app])
    while not tok:
        login = ask_login(app)
        if not login:
            note(app, "-", "skipped")
            return {}
        tok, why = ha_token(*login)
        if not tok:
            say("    " + why + ". Try again.")
        else:
            ask_owner(app, login[0], people, pw)
    ws = WebSocket(HOST, PORTS[app], "/api/websocket")
    try:
        if ws.recv().get("type") != "auth_required":
            raise ConnectionError("unexpected first message")
        ws.send({"type": "auth", "access_token": tok})
        if ws.recv().get("type") != "auth_ok":
            note(app, "-", "FAILED: token not accepted")
            return {}
        r = ws.call(type="config/auth/list")
        if not r.get("success"):
            note(app, "-", "FAILED: that account is not an administrator (%s)" % short(r.get("error")))
            return {}
        users = [u for u in r["result"] if not u.get("system_generated")]
        known = {(u.get("username") or "").lower() for u in users} | {(u.get("name") or "").lower() for u in users}
        done = {}
        for p in people:
            if p["type"] in ("family", "guest"):
                continue
            mine = (linked(pw, app, p["login"]) or "").lower()
            if p["login"] in known or p["nick"].lower() in known or (mine and mine in known):
                note(app, p["login"], "already there (password not changed)")
                done[p["login"]] = (mine or p["login"], False)
                continue
            admin = p["type"] == "admin"
            r = ws.call(type="config/auth/create", name=p["nick"],
                        group_ids=["system-admin" if admin else "system-users"], local_only=True)
            if not r.get("success"):
                note(app, p["login"], "FAILED to create (%s)" % short(r.get("error")))
                continue
            uid = r["result"]["user"]["id"]
            r = ws.call(**{"type": "config/auth_provider/homeassistant/create", "user_id": uid,
                           "username": p["login"], "password": password_for(p, app, pw)})
            if not r.get("success"):
                ws.call(type="config/auth/delete", user_id=uid)      # don't leave a half-made user behind
                note(app, p["login"], "FAILED to set the login (%s)" % short(r.get("error")))
                continue
            ws.call(type="person/create", name=p["nick"], user_id=uid)
            note(app, p["login"], "created" + (" (admin)" if admin else " (home network only)"))
            done[p["login"]] = (p["login"], True)
        return done
    finally:
        ws.close()


# ================================================================ CaciqueVault (Vaultwarden) invitations
def do_vaultwarden(people):
    app = "vaultwarden"
    tpath = os.path.join(ACC, "vaultwarden-admin-token.txt")
    if not os.path.exists(tpath):
        note(app, "-", "skipped (run vaultwarden/setup-vault.sh first)")
        return {}
    token = open(tpath).read().strip()
    st, hdrs, _ = call(PORTS[app], "POST", "/admin", form={"token": token})
    cookie = None
    for c in hdrs.get("set-cookie", []):
        m = re.match(r"\s*(VW_ADMIN=[^;]+)", c)
        if m:
            cookie = m.group(1)
    if not cookie:
        note(app, "-", "FAILED: the admin key was not accepted (%s)" % st)
        return {}
    H = {"Cookie": cookie}
    st, _, users = call(PORTS[app], "GET", "/admin/users", headers=H)
    have = {u.get("email", "").lower() for u in users} if isinstance(users, list) else set()
    done = {}
    for p in people:
        if p["type"] in ("family", "guest"):
            continue
        if p["email"] in have:
            note(app, p["login"], "already invited")
        else:
            st, _, d = call(PORTS[app], "POST", "/admin/invite", {"email": p["email"]}, H)
            if st not in (200, 201, 409):
                note(app, p["login"], "FAILED to invite (%s %s)" % (st, short(d)))
                continue
            note(app, p["login"], "invited (they create their own master password)")
        done[p["login"]] = (p["email"], True)
    return done


# ================================================================ cards + import file
def write_outputs(people, pw, made, ip):
    cards = os.path.join(ACC, "cards")
    os.makedirs(cards, mode=0o700, exist_ok=True)
    urls = {"jellyfin": "http://%s:8096" % ip, "immich": "http://%s:2283" % ip, "paperless": "http://%s:8000" % ip,
            "romm": "http://%s:8090" % ip, "homeassistant": "http://%s:8123" % ip, "vaultwarden": "https://%s:8443" % ip}
    login_word = {"jellyfin": "nombre / name", "immich": "correo / email", "paperless": "usuario / user",
                  "romm": "usuario / user", "homeassistant": "usuario / user"}
    open_link = ""
    try:
        open_link = open(os.path.join(ACC, "open-photos-link.txt")).read().strip()
    except Exception:
        pass

    for p in people:
        if p["type"] != "adult":
            continue
        lines = ["EL CACIQUE HOME LAB", "", "¡Hola, %s! · Hi, %s!" % (p["nick"], p["nick"]), "",
                 "Contraseña inicial / Starter password:   %s" % pw["people"][p["login"]],
                 "(Cámbiala cuando entres. Change it after you log in.)", "",
                 "Dónde usarla / Where to use it:"]
        for app in ("jellyfin", "immich", "paperless", "romm", "homeassistant"):
            if p["login"] in made.get(app, {}):
                value, created = made[app][p["login"]]
                lines.append("  %-14s %-26s %s: %s%s" % (NAMES[app], urls[app], login_word[app], value,
                             "" if created else "   (ya tenías cuenta: tu contraseña de siempre / existing account: your usual password)"))
        if p["login"] in made.get("vaultwarden", {}):
            lines += ["", "TU CAJA FUERTE DE CONTRASEÑAS / YOUR PASSWORD SAFE (CaciqueVault)",
                      "  1. Una vez por equipo / once per device: abre / open  http://%s/cacique-ca.crt" % ip,
                      "     e instálalo / and install it (El Cacique te ayuda / El Cacique will help).",
                      "  2. Abre / open  %s  ->  \"Create account\"" % urls["vaultwarden"],
                      "     correo / email:  %s" % p["email"],
                      "     Inventa una CONTRASEÑA MAESTRA que solo tú sepas. Si la olvidas, NADIE puede abrir tu caja.",
                      "     Make up a MASTER PASSWORD only you know. If you forget it, NOBODY can open your safe.",
                      "  3. App Bitwarden -> \"self-hosted\" / \"Autoalojado\" -> server URL:  %s" % urls["vaultwarden"],
                      "  4. Guarda ahí tus contraseñas nuevas. Save your new passwords there."]
        lines += ["", "Dirección de la casa / Home address:  http://%s" % ip]
        path = os.path.join(cards, "%s.txt" % p["login"])
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    # El Cacique's logins, ready to import into El Cacique's own CaciqueVault (Bitwarden CSV format)
    rows = [["folder", "favorite", "type", "name", "notes", "fields", "reprompt",
             "login_uri", "login_username", "login_password", "login_totp"]]
    ec = next(p for p in people if p["type"] == "admin")
    for app in ("jellyfin", "immich", "paperless", "romm", "homeassistant"):
        if ec["login"] in made.get(app, {}):
            rows.append(["El Cacique", "", "login", "El Cacique · %s" % NAMES[app], "Administrator account",
                         "", "1", urls[app], made[app][ec["login"]][0], pw["elcacique"][app], ""])
    tpath = os.path.join(ACC, "vaultwarden-admin-token.txt")
    if os.path.exists(tpath):
        rows.append(["El Cacique", "", "login", "El Cacique · CaciqueVault admin page", "Admin key for /admin",
                     "", "1", urls["vaultwarden"] + "/admin", "", open(tpath).read().strip(), ""])
    if open_link:
        rows.append(["El Cacique", "", "login", "Familia Abierta (visitor slideshow)", "Link for guests and family",
                     "", "0", open_link, "", "", ""])

    def csv_cell(v):
        v = str(v)
        return '"%s"' % v.replace('"', '""') if any(c in v for c in ',"\n') else v
    path = os.path.join(ACC, "for-vaultwarden-import.csv")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(",".join(csv_cell(c) for c in r) for r in rows) + "\n")
    return cards, path



# ================================================================ fixing "whose account is this?" answers
# python3 create_accounts.py --fix-owners   (bash accounts/fix-owners.sh)
# For each app: shows the accounts that existed before (not made by this tool), asks whose each one is,
# then offers to delete any EXTRA account this tool made by mistake. It only deletes an account that
# still opens with its untouched starter password (so it was never used), and only if you type "y".

class AppAdapter:
    """What fix-owners needs from each app: list accounts, test a starter password, delete one."""

    def __init__(self, app, people, pw):
        self.app, self.people, self.pw = app, people, pw
        self.ok = False

    def default_ident(self, p):
        return p["login"]


class JellyfinAdapter(AppAdapter):
    def connect(self):
        tok, _ = jf_login("El Cacique", self.pw["elcacique"]["jellyfin"])
        self.H = jf_auth(tok) if tok else None
        return bool(tok)

    def default_ident(self, p):
        return p["nick"]

    def accounts(self):
        st, _, users = call(PORTS["jellyfin"], "GET", "/Users", headers=self.H)
        return [(u["Id"], u["Name"], u["Name"]) for u in users] if st == 200 else []

    def starter_works(self, ident, password):
        st, _, _ = call(PORTS["jellyfin"], "POST", "/Users/AuthenticateByName", {"Username": ident, "Pw": password}, jf_auth())
        return st == 200

    def delete(self, uid):
        st, _, _ = call(PORTS["jellyfin"], "DELETE", "/Users/%s" % uid, headers=self.H)
        return st in (200, 204)


class ImmichAdapter(AppAdapter):
    def connect(self):
        ec = next(p for p in self.people if p["type"] == "admin")
        tok, _ = im_login(ec["email"], self.pw["elcacique"]["immich"])
        self.H = {"Authorization": "Bearer " + tok} if tok else None
        return bool(tok)

    def default_ident(self, p):
        return p["email"]

    def accounts(self):
        st, _, users = call(PORTS["immich"], "GET", "/api/admin/users", headers=self.H)
        return [(u["id"], u["email"], u.get("name", "")) for u in users] if st == 200 else []

    def starter_works(self, ident, password):
        return bool(im_login(ident, password)[0])

    def delete(self, uid):
        st, _, _ = call(PORTS["immich"], "DELETE", "/api/admin/users/%s" % uid, {"force": False}, self.H)
        return st in (200, 204)


class PaperlessAdapter(AppAdapter):
    def connect(self):
        self.H = pl_headers("elcacique", self.pw["elcacique"]["paperless"])
        return pl_check(self.H)

    def accounts(self):
        st, _, d = call(PORTS["paperless"], "GET", "/api/users/?page_size=1000", headers=self.H)
        return [(u["id"], u["username"], u.get("first_name", "")) for u in d["results"]] if st == 200 else []

    def starter_works(self, ident, password):
        st, _, _ = call(PORTS["paperless"], "GET", "/api/ui_settings/", headers=pl_headers(ident, password))
        return st == 200

    def delete(self, uid):
        st, _, _ = call(PORTS["paperless"], "DELETE", "/api/users/%s/" % uid, headers=self.H)
        return st in (200, 204)


class RommAdapter(AppAdapter):
    def connect(self):
        tok = rm_token("elcacique", self.pw["elcacique"]["romm"])
        self.H = {"Authorization": "Bearer " + tok} if tok else None
        return bool(tok)

    def accounts(self):
        st, _, users = call(PORTS["romm"], "GET", "/api/users", headers=self.H)
        return [(u["id"], u["username"], u["username"]) for u in users] if st == 200 else []

    def starter_works(self, ident, password):
        st, _, _ = call(PORTS["romm"], "POST", "/api/token", form={
            "grant_type": "password", "username": ident, "password": password, "scope": "me.read"})
        return st == 200

    def delete(self, uid):
        st, _, _ = call(PORTS["romm"], "DELETE", "/api/users/%s" % uid, headers=self.H)
        return st in (200, 204)


class HomeAssistantAdapter(AppAdapter):
    def connect(self):
        tok, _ = ha_token("elcacique", self.pw["elcacique"]["homeassistant"])
        if not tok:
            return False
        self.ws = WebSocket(HOST, PORTS["homeassistant"], "/api/websocket")
        self.ws.recv()
        self.ws.send({"type": "auth", "access_token": tok})
        return self.ws.recv().get("type") == "auth_ok"

    def accounts(self):
        r = self.ws.call(type="config/auth/list")
        return [(u["id"], u.get("username") or u.get("name"), u.get("name", ""))
                for u in r.get("result", []) if not u.get("system_generated")]

    def starter_works(self, ident, password):
        return bool(ha_token(ident, password)[0])

    def delete(self, uid):
        persons = self.ws.call(type="person/list").get("result", {})
        for person in persons.get("storage", []):
            if person.get("user_id") == uid:
                self.ws.call(type="person/delete", person_id=person["id"])
        return bool(self.ws.call(type="config/auth/delete", user_id=uid).get("success"))


ADAPTERS = {"jellyfin": JellyfinAdapter, "immich": ImmichAdapter, "paperless": PaperlessAdapter,
            "romm": RommAdapter, "homeassistant": HomeAssistantAdapter}


def fix_owners(people, pw):
    adults = [p for p in people if p["type"] == "adult"]
    logins = [p["login"] for p in adults]
    links_all = pw.setdefault("links", {})
    for app, cls in ADAPTERS.items():
        say("")
        say("== %s ==" % NAMES[app])
        if not is_up(PORTS[app]):
            say("  not running - skipped")
            continue
        ad = cls(app, people, pw)
        try:
            if not ad.connect():
                say("  El Cacique can't log in here yet - run create-accounts.sh first. Skipped.")
                continue
            accounts = ad.accounts()
            ours = {ad.default_ident(p).lower() for p in people}
            links = links_all.setdefault(app, {})
            # 1. accounts that existed before: whose are they?
            older = [a for a in accounts if (a[1] or "").lower() not in ours]
            if not older:
                say("  No older accounts here.")
            for uid, ident, name in older:
                now = next((who for who, v in links.items() if v.lower() == ident.lower()), "")
                say("  Account \"%s\"%s - right now it belongs to: %s" % (
                    ident, (" (%s)" % name) if name and name != ident else "", now or "nobody on the list"))
                try:
                    ans = input("    whose is it? type a login (%s), \"none\", or Enter to keep: " % ", ".join(logins)).strip().lower()
                except EOFError:
                    ans = ""
                if ans == "none":
                    for who in [w for w, v in links.items() if v.lower() == ident.lower()]:
                        del links[who]
                    say("    OK: it's nobody's personal account now.")
                elif ans in logins:
                    for who in [w for w, v in links.items() if v.lower() == ident.lower() or w == ans]:
                        del links[who]
                    links[ans] = ident
                    say("    OK: \"%s\" is %s's account." % (ident, ans))
                elif ans:
                    say("    \"%s\" is not on the list - nothing changed." % ans)
            save_json(os.path.join(ACC, "passwords.json"), pw)
            # 2. extra accounts made by mistake for someone who already had one
            by_ident = {(a[1] or "").lower(): a for a in accounts}
            for p in adults:
                mine = links.get(p["login"])
                extra = by_ident.get(ad.default_ident(p).lower())
                if not mine or not extra or extra[1].lower() == mine.lower():
                    continue
                if not ad.starter_works(extra[1], pw["people"].get(p["login"], "")):
                    say("  %s has an extra account \"%s\", but it was already used (its starter password changed)." % (p["login"], extra[1]))
                    say("    Not touching it. Delete it by hand in %s if you don't want it." % NAMES[app])
                    continue
                try:
                    ans = input("  Extra account \"%s\" was made for %s by mistake (they already have \"%s\"). Delete it? (y/N): "
                                % (extra[1], p["login"], mine)).strip().lower()
                except EOFError:
                    ans = ""
                if ans in ("y", "yes", "s", "si", "sí"):
                    say("    Deleted." if ad.delete(extra[0]) else "    Could not delete it - remove it by hand in %s." % NAMES[app])
                else:
                    say("    Kept.")
        except Exception as e:
            say("  FAILED: %s: %s" % (e.__class__.__name__, short(str(e))))
        finally:
            if getattr(ad, "ws", None):
                ad.ws.close()

# ================================================================ main
def main():
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    people = load_people()
    if not any(p["type"] == "admin" for p in people):
        sys.exit("  The El Cacique admin line is missing from people.txt (run people.sh list to recreate it).")
    if not any(p["type"] == "adult" for p in people):
        say("  [WARN] No adults on the list yet. Add them with: bash ~/elcaciquedeck/accounts/people.sh add <login> <nickname>")
    pw = load_passwords(people)
    ip = laptop_ip()
    say("  People: " + ", ".join("%s (%s)" % (p["nick"], p["type"]) for p in people))
    if "--fix-owners" in sys.argv:
        fix_owners(people, pw)
        say("")
        say("  Now making anything that's missing and refreshing the cards...")
    made = {}
    steps = [("jellyfin", lambda: do_jellyfin(people, pw)), ("immich", lambda: do_immich(people, pw, ip)),
             ("paperless", lambda: do_paperless(people, pw)), ("romm", lambda: do_romm(people, pw)),
             ("homeassistant", lambda: do_homeassistant(people, pw)), ("vaultwarden", lambda: do_vaultwarden(people))]
    for app, fn in steps:
        if only and app not in only:
            continue
        say("")
        say("== %s ==" % NAMES[app])
        if not is_up(PORTS[app]):
            note(app, "-", "skipped: not running (start it with start-all.sh, then run this again)")
            continue
        try:
            made[app] = fn() or {}
        except Exception as e:      # one app failing never stops the others
            note(app, "-", "FAILED: %s: %s" % (e.__class__.__name__, short(str(e))))
    cards, csv_path = write_outputs(people, pw, made, ip)
    fails = [r for r in report if "FAILED" in r[2]]
    say("")
    say("== Done ==")
    say("  Cards for each adult (starter password + where to use it):  %s/" % cards)
    say("  El Cacique's logins, to import into CaciqueVault:            %s" % csv_path)
    say("  %d problems." % len(fails) if fails else "  No problems.")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
