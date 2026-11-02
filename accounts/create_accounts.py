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
PORTS = {"adguard": 3000, "jellyfin": 8096, "immich": 2283, "paperless": 8000, "romm": 8090, "homeassistant": 8123, "vaultwarden": 8222}
NAMES = {"adguard": "CaciqueGuard", "jellyfin": "CaciqueFlix", "immich": "CaciquePhotos", "paperless": "CaciqueDocs", "romm": "CaciqueArcade",
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
ADMIN = {"jellyfin": "El Cacique", "immich": "elcacique@cacique.home", "paperless": "elcacique",
         "romm": "elcacique", "homeassistant": "elcacique"}     # replaced from people.txt in main()


def set_admin(people):
    a = next(p for p in people if p["type"] == "admin")
    ADMIN.update(jellyfin=a["nick"], immich=a["email"], paperless=a["nick"], romm=a["login"], homeassistant=a["login"])


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
        try:
            conn.request(method, path, body=data, headers=h)
            r = conn.getresponse()
            raw = r.read()
        except (socket.timeout, TimeoutError):
            raise TimeoutError("no answer from %s %s (port %d) after %d seconds" % (method, path.split("?")[0], port, timeout))
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
    for app in ("jellyfin", "immich", "paperless", "romm", "homeassistant", "adguard"):
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


def set_admin_login(people):
    """--set-admin NAME : the same admin name and password in every app (asked twice, hidden)."""
    name = sys.argv[sys.argv.index("--set-admin") + 1] if len(sys.argv) > sys.argv.index("--set-admin") + 1 else ""
    if not re.match(r"^[A-Za-z][A-Za-z0-9]{2,30}$", name):
        sys.exit("  Admin name: letters and numbers only (example: ElCaciqueAdmin)")
    p1 = getpass.getpass("  Admin password for every app (won't show): ")
    p2 = getpass.getpass("  Type it again: ")
    if p1 != p2 or len(p1) < 8:
        sys.exit("  The two passwords don't match, or it's shorter than 8 characters. Nothing changed.")
    path = os.path.join(ACC, "people.txt")
    lines = [l for l in open(path, encoding="utf-8").read().splitlines() if not l.endswith("|admin")]
    lines.insert(2 if len(lines) >= 2 else len(lines), "%s|%s|admin" % (name.lower(), name))
    fd = os.open(path, os.O_WRONLY | os.O_TRUNC | os.O_CREAT, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    people = load_people()
    pw = load_passwords(people)
    for app in ("jellyfin", "immich", "paperless", "romm", "homeassistant", "adguard"):
        pw["elcacique"][app] = p1
    save_json(os.path.join(ACC, "passwords.json"), pw)
    say("  OK: the admin is \"%s\" (CaciquePhotos email: %s@%s) with that password in every app." % (name, name.lower(), EMAIL_DOMAIN))
    return 0


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


JF_LAST = {"why": ""}


def jf_login(user, password):
    st, _, d = call(PORTS["jellyfin"], "POST", "/Users/AuthenticateByName", {"Username": user, "Pw": password}, jf_auth())
    if st == 200 and isinstance(d, dict) and d.get("AccessToken"):
        if not d.get("User", {}).get("Policy", {}).get("IsAdministrator"):
            JF_LAST["why"] = "that account works, but it is not an administrator in CaciqueFlix"
            return None, None
        return d["AccessToken"], d["User"]["Id"]
    JF_LAST["why"] = "CaciqueFlix answered %s: %s" % (st, short(d, 200) if d else "(no message)")
    return None, None


def jf_flatpak_dir():
    return os.path.join(HOME, ".var", "app", "org.jellyfin.JellyfinServer")


def jf_pin_reset(user):
    """Jellyfin's own 'Forgot password' (only works from this laptop): the new password becomes the PIN."""
    port = PORTS["jellyfin"]
    st, _, d = call(port, "POST", "/Users/ForgotPassword", {"EnteredUsername": user}, jf_auth())
    if st != 200 or not isinstance(d, dict) or d.get("Action") != "PinCode":
        say("    CaciqueFlix would not start a reset for \"%s\" (%s %s). Check the name." % (user, st, short(d)))
        return None
    pin_file = d.get("PinFile") or ""
    candidates = [pin_file] if os.path.exists(pin_file) else []
    for root, _dirs, files in os.walk(jf_flatpak_dir()):
        candidates += [os.path.join(root, f) for f in files if f.startswith("passwordreset") and f.endswith(".json")]
    for path in candidates:
        try:
            pin = json.load(open(path, encoding="utf-8-sig"))["Pin"].replace("-", "")
        except Exception:
            continue
        # Jellyfin sets the new password to exactly the PIN text we send, so send it without dashes
        st, _, res = call(port, "POST", "/Users/ForgotPassword/Pin", {"Pin": pin}, jf_auth())
        if st == 200 and isinstance(res, dict) and res.get("Success"):
            return pin
    say("    Could not find or use the reset PIN file (looked in %s)." % jf_flatpak_dir())
    return None


def jf_unlock(user):
    """Jellyfin locks an account after too many wrong passwords. Unlock it in its database (Jellyfin is stopped first)."""
    import glob, shutil, sqlite3, time
    dbs = glob.glob(os.path.join(jf_flatpak_dir(), "**", "jellyfin.db"), recursive=True)
    if not dbs:
        say("    Could not find CaciqueFlix's database under %s." % jf_flatpak_dir())
        return False
    db = dbs[0]
    say("    Stopping CaciqueFlix for a moment...")
    subprocess.run(["flatpak", "kill", "org.jellyfin.JellyfinServer"], capture_output=True)
    for _ in range(30):
        if not is_up(PORTS["jellyfin"]):
            break
        time.sleep(1)
    time.sleep(2)
    shutil.copy2(db, db + ".before-unlock")
    try:
        con = sqlite3.connect(db)
        row = con.execute("SELECT Id FROM Users WHERE Username = ? COLLATE NOCASE", (user,)).fetchone()
        if not row:
            say("    No account called \"%s\" in CaciqueFlix." % user)
        else:
            con.execute("UPDATE Permissions SET Value = 0 WHERE UserId = ? AND Kind = 2", (row[0],))
            con.execute("UPDATE Users SET InvalidLoginAttemptCount = 0 WHERE Id = ?", (row[0],))
            con.commit()
            say("    \"%s\" is unlocked (a copy of the old database: %s.before-unlock)." % (user, db))
        con.close()
    finally:
        say("    Starting CaciqueFlix again...")
        log = open(os.path.join(ACC, "jellyfin-restart.log"), "w")
        subprocess.Popen(["flatpak", "run", "org.jellyfin.JellyfinServer"], stdout=log, stderr=log, start_new_session=True)
        for _ in range(90):
            if is_up(PORTS["jellyfin"]):
                break
            time.sleep(1)
        time.sleep(5)
    return bool(row)


def yes(question):
    try:
        return input(question).strip().lower() in ("y", "yes", "s", "si", "sí")
    except EOFError:
        return False


def jf_help(user):
    """After a failed CaciqueFlix login: say why, and offer the fixes."""
    why = JF_LAST["why"]
    say("    It didn't work - " + why)
    st, _, names = call(PORTS["jellyfin"], "GET", "/Users/Public", headers=jf_auth())
    if st == 200 and isinstance(names, list) and names:
        say("    Accounts shown on the CaciqueFlix login screen: " + ", ".join(n.get("Name", "?") for n in names))
    if "disabled" in why.lower():
        say("    CaciqueFlix LOCKED \"%s\" after too many wrong passwords." % user)
        if yes("    Unlock it now? (y/N): ") and jf_unlock(user):
            say("    Now type the name and password again.")
        return None
    if "Invalid username or password" in why:
        say("    If you're sure of the name but not the password, CaciqueFlix can reset it with a PIN")
        say("    (the new password becomes the PIN; you change it later in CaciqueFlix -> Profile -> Password).")
        if yes("    Reset the password of \"%s\" now? (y/N): " % user):
            pin = jf_pin_reset(user)
            if pin:
                say("    Done. The password of \"%s\" is now:  %s   (write it down, change it later)" % (user, pin))
                return pin
    return None


def do_jellyfin(people, pw):
    app = "jellyfin"
    tok, me = jf_login(ADMIN["jellyfin"], pw["elcacique"][app])
    if not tok and pw.get("reset", {}).get(app):
        tok, me = jf_login(*pw["reset"][app])
        if tok:
            ask_owner(app, pw["reset"][app][0], people, pw)
    while not tok:
        login = ask_login(app)
        if not login:
            note(app, "-", "skipped")
            return {}
        tok, me = jf_login(*login)
        if not tok:
            new_pw = jf_help(login[0])
            if new_pw:
                tok, me = jf_login(login[0], new_pw)
        if tok:
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
    if not tok and pw.get("reset", {}).get(app):
        tok, me = im_login(*pw["reset"][app])
        if tok:
            ask_owner(app, pw["reset"][app][0], people, pw)
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


PL_LAST = {"why": ""}


def pl_check(H):
    st, _, d = call(PORTS["paperless"], "GET", "/api/users/?page_size=1000", headers=H)
    ok = st == 200 and isinstance(d, dict) and "results" in d
    if not ok:
        PL_LAST["why"] = "CaciqueDocs answered %s: %s" % (st, short(d, 200) if d else "(no message)")
    return ok


def pl_make_elcacique(password):
    """Make (or repair) the El Cacique superuser from inside the CaciqueDocs server: no old password needed."""
    code = ("import os; from django.contrib.auth.models import User; "
            "u, _ = User.objects.get_or_create(username=os.environ['CQ_USER']); "
            "u.set_password(os.environ['CQ_PW']); u.is_superuser = True; u.is_staff = True; u.is_active = True; "
            "u.first_name = os.environ['CQ_USER']; u.email = os.environ['CQ_MAIL']; u.save(); print('elcacique-ok')")
    compose = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "paperless")
    r = subprocess.run(["docker", "compose", "exec", "-T", "-e", "CQ_PW=" + password, "-e", "CQ_USER=" + ADMIN["paperless"],
                        "-e", "CQ_MAIL=" + ADMIN["immich"], "webserver",
                        "python3", "manage.py", "shell", "-c", code],
                       cwd=compose, capture_output=True, text=True, timeout=180)
    if "elcacique-ok" in r.stdout:
        return True
    say("    Could not do it: " + short((r.stderr or r.stdout).strip()[-300:], 300))
    return False


def do_paperless(people, pw):
    app = "paperless"
    H = pl_headers(ADMIN["paperless"], pw["elcacique"][app])
    while not pl_check(H):
        login = ask_login(app)
        if not login:
            note(app, "-", "skipped")
            return {}
        H = pl_headers(*login)
        if not pl_check(H):
            say("    It didn't work - " + PL_LAST["why"])
            if "403" in PL_LAST["why"].split(":")[0]:
                say("    The name and password are right, but that account is not an admin in CaciqueDocs.")
            elif "MFA" in PL_LAST["why"]:
                say("    That account uses a second step (MFA), which this tool can't type for you.")
            else:
                say("    (Names in CaciqueDocs care about capital letters: Jonnatan is not jonnatan.)")
            say("    Or skip the old login: I can make the El Cacique admin directly inside the CaciqueDocs server.")
            if yes("    Make El Cacique directly now? (y/N): "):
                if pl_make_elcacique(pw["elcacique"][app]):
                    say("    El Cacique is ready in CaciqueDocs.")
                    H = pl_headers(ADMIN["paperless"], pw["elcacique"][app])
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
        if admin and ADMIN["paperless"].lower() in by_name:
            note(app, p["login"], "already there (password not changed)")
            done[p["login"]] = (ADMIN["paperless"], False)
            continue
        body = {"username": ADMIN["paperless"] if admin else p["login"], "password": password_for(p, app, pw), "first_name": p["nick"],
                "email": p["email"], "is_staff": admin, "is_superuser": admin, "is_active": True,
                "groups": [] if admin or not group else [group["id"]]}
        st, _, u = call(PORTS[app], "POST", "/api/users/", body, H)
        if st not in (200, 201) and admin and pl_make_elcacique(pw["elcacique"][app]):
            st = 201          # CaciqueDocs refuses very simple passwords through its API; made directly instead
        if st in (200, 201):
            note(app, p["login"], "created" + (" (superuser)" if admin else " (own private documents)"))
            done[p["login"]] = (body["username"], True)
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
    tok = rm_token(ADMIN["romm"], pw["elcacique"][app])
    if not tok:
        st, _, u = call(PORTS[app], "POST", "/api/users", {"username": ADMIN["romm"], "email": ADMIN["immich"],
                                                          "password": pw["elcacique"][app], "role": "admin"})
        if st in (200, 201):
            note(app, ADMIN["romm"], "created as the first CaciqueArcade admin")
            tok = rm_token(ADMIN["romm"], pw["elcacique"][app])
    if not tok and pw.get("reset", {}).get(app):
        tok = rm_token(*pw["reset"][app])
        if tok:
            ask_owner(app, pw["reset"][app][0], people, pw)
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


def ha_onboard_owner(name, username, password):
    """Fresh Home Assistant (first-time setup never finished): make the admin its owner."""
    port = PORTS["homeassistant"]
    st, _, steps = call(port, "GET", "/api/onboarding")
    if st != 200 or not isinstance(steps, list):
        return None
    if any(x.get("step") == "user" and x.get("done") for x in steps):
        return None
    cid = "http://%s:%d/" % (HOST, port)
    st, _, d = call(port, "POST", "/api/onboarding/users", {"client_id": cid, "name": name, "username": username,
                                                           "password": password, "language": "es"})
    if st != 200 or not isinstance(d, dict) or not d.get("auth_code"):
        say("    CaciqueHome first-time setup refused: %s %s" % (st, short(d)))
        return None
    st, _, t = call(port, "POST", "/auth/token", form={"grant_type": "authorization_code",
                                                         "code": d["auth_code"], "client_id": cid})
    tok = t.get("access_token") if isinstance(t, dict) else None
    if tok:      # finish the remaining first-time screens (location defaults, no analytics)
        H = {"Authorization": "Bearer " + tok}
        call(port, "POST", "/api/onboarding/core_config", {}, H)
        call(port, "POST", "/api/onboarding/analytics", {}, H)
        call(port, "POST", "/api/onboarding/integration", {"client_id": cid, "redirect_uri": cid + "?auth_callback=1"}, H)
    return tok


def do_homeassistant(people, pw):
    app = "homeassistant"
    tok, why = ha_token(ADMIN["homeassistant"], pw["elcacique"][app])
    if not tok:
        ec = next(p for p in people if p["type"] == "admin")
        tok = ha_onboard_owner(ec["nick"], ADMIN["homeassistant"], pw["elcacique"][app])
        if tok:
            note(app, ADMIN["homeassistant"], "created as the CaciqueHome owner (first-time setup finished)")
    if not tok and pw.get("reset", {}).get(app):
        tok, why = ha_token(*pw["reset"][app])
        if tok:
            ask_owner(app, pw["reset"][app][0], people, pw)
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
    st, hdrs, _ = call(PORTS[app], "POST", "/admin", form={"token": token}, timeout=60)
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


# ================================================================ CaciqueGuard (AdGuard Home)
def bcrypt_hash(password):
    try:
        import bcrypt     # if Ubuntu has it
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    except Exception:
        return romm_hash(password)     # borrow CaciqueArcade's copy


def do_adguard(pw):
    app = "adguard"
    conf = os.path.join(REPO_DIR, "adguard", "conf", "AdGuardHome.yaml")
    rc, text = sh(["sudo", "-n", "cat", conf], timeout=30)
    if rc != 0:
        note(app, "-", "skipped: can't read %s (%s)" % (conf, short(text, 120)))
        return
    name = ADMIN["paperless"]
    if re.search(r"^\s*-\s*name:\s*%s\s*$" % re.escape(name), text, re.M):
        note(app, name, "already there (password not changed)")
        return
    h = bcrypt_hash(pw["elcacique"][app])
    if not h:
        note(app, name, "FAILED: could not make the password code")
        return
    entry = "  - name: %s\n    password: %s\n" % (name, h)
    if re.search(r"^users:\s*\[\]\s*$", text, re.M):
        new = re.sub(r"^users:\s*\[\]\s*$", "users:\n" + entry.rstrip("\n"), text, count=1, flags=re.M)
    elif re.search(r"^users:\s*$", text, re.M):
        new = re.sub(r"^users:\s*$", "users:\n" + entry.rstrip("\n"), text, count=1, flags=re.M)
    else:
        note(app, name, "FAILED: no users list in AdGuard's settings")
        return
    sh(["sudo", "-n", "cp", conf, conf + ".before-elcacique"], timeout=30)
    rc, out = sh(["sudo", "-n", "tee", conf], inp=new, timeout=30)
    if rc != 0:
        note(app, name, "FAILED to save: " + short(out))
        return
    sh(["docker", "restart", "caciqueguard"], timeout=120)
    note(app, name, "created (CaciqueGuard restarted; old settings kept as AdGuardHome.yaml.before-elcacique)")


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
        tok, _ = jf_login(ADMIN["jellyfin"], self.pw["elcacique"]["jellyfin"])
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
        self.H = pl_headers(ADMIN["paperless"], self.pw["elcacique"]["paperless"])
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
        tok = rm_token(ADMIN["romm"], self.pw["elcacique"]["romm"])
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
        tok, _ = ha_token(ADMIN["homeassistant"], self.pw["elcacique"]["homeassistant"])
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


# ================================================================ "I don't know any admin password"
# python3 create_accounts.py --reset-admins   (bash accounts/reset-admins.sh)
# Gets admin access to each app WITHOUT the old passwords, using each app's own recovery tool on this laptop:
#   CaciqueFlix   Jellyfin's "forgot password" PIN (+ unlock if it got locked)  -> your admin gets a new password
#   CaciquePhotos immich-admin reset-admin-password                             -> your admin gets a new password
#   CaciqueDocs   makes El Cacique directly (your own account is not touched)
#   CaciqueArcade sets a new password on the admin you choose (database)
#   CaciqueHome   sets a new password on the login you choose (HA's own "auth" tool; restarts CaciqueHome)
# The new passwords are shown on screen and saved (private) in ~/elcaciquedeck-data/accounts/new-admin-passwords.txt.
# Then the normal run uses them by itself to make El Cacique and everyone's accounts.

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sh(args, cwd=None, inp=None, timeout=300):
    try:
        r = subprocess.run(args, cwd=cwd, input=inp, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return 1, "%s: %s" % (e.__class__.__name__, e)


def pick(label, options):
    """Ask which one of a short list (number or name). Returns the chosen value or None."""
    if not options:
        return None
    say("    These are the admin logins that exist today. Yours may have an older name (not \"jonnatan\");")
    say("    pick the one you used to manage this app - it gets a new password and becomes yours.")
    if len(options) == 1:
        if yes("    %s: \"%s\" - use this one? (y/N): " % (label, options[0])):
            return options[0]
        return None
    for i, o in enumerate(options, 1):
        say("      %d) %s" % (i, o))
    try:
        a = input("    %s - type its number (or Enter to skip): " % label).strip()
    except EOFError:
        return None
    if a.isdigit() and 1 <= int(a) <= len(options):
        return options[int(a) - 1]
    return None


def remember_reset(pw, app, user, password, shown_name):
    pw.setdefault("reset", {})[app] = [user, password]
    save_json(os.path.join(ACC, "passwords.json"), pw)
    path = os.path.join(ACC, "new-admin-passwords.txt")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as f:
        f.write("%-14s %-30s %s\n" % (NAMES[app], shown_name, password))
    say("    NEW PASSWORD for %s in %s:   %s" % (shown_name, NAMES[app], password))


def reset_jellyfin(pw):
    import glob, shutil, sqlite3, tempfile
    dbs = glob.glob(os.path.join(jf_flatpak_dir(), "**", "jellyfin.db"), recursive=True)
    names = []
    if dbs:
        tmp = tempfile.mkdtemp()
        for ext in ("", "-wal", "-shm"):
            if os.path.exists(dbs[0] + ext):
                shutil.copy2(dbs[0] + ext, os.path.join(tmp, "j.db" + ext))
        try:
            con = sqlite3.connect(os.path.join(tmp, "j.db"))
            names = [r[0] for r in con.execute(
                "SELECT u.Username FROM Users u JOIN Permissions p ON p.UserId = u.Id WHERE p.Kind = 0 AND p.Value = 1")]
            locked = {r[0] for r in con.execute(
                "SELECT u.Username FROM Users u JOIN Permissions p ON p.UserId = u.Id WHERE p.Kind = 2 AND p.Value = 1")}
            con.close()
        except Exception as e:
            say("    Could not read the CaciqueFlix account list (%s)." % e)
            locked = set()
        shutil.rmtree(tmp, ignore_errors=True)
    else:
        locked = set()
    if not names:
        try:
            names = [input("    Type the CaciqueFlix admin name (as it shows on its login screen): ").strip()]
        except EOFError:
            return
    say("    CaciqueFlix admin accounts: " + ", ".join(names))
    user = pick("Which admin should get a new password", names)
    if not user:
        say("    Skipped.")
        return
    if user in locked:
        say("    \"%s\" is locked (too many wrong passwords). Unlocking it first..." % user)
        jf_unlock(user)
    pin = jf_pin_reset(user)
    if pin and jf_login(user, pin)[0]:
        remember_reset(pw, "jellyfin", user, pin, user)
    else:
        say("    It didn't work: " + JF_LAST["why"])


def run_with_terminal(args, answers, timeout=90):
    """Run a program that insists on a real terminal; answer its questions in order.
    answers = [(text the program shows, what to type), ...]. Gives up after `timeout` seconds."""
    import pty, select, signal, time
    pid, fd = pty.fork()
    if pid == 0:
        try:
            os.execvp(args[0], args)
        finally:
            os._exit(127)
    out, seen, todo, start = "", 0, list(answers), time.time()
    try:
        while time.time() - start < timeout:
            ready, _, _ = select.select([fd], [], [], 1)
            if not ready:
                continue
            try:
                data = os.read(fd, 4096)
            except OSError:
                break
            if not data:
                break
            out += data.decode(errors="replace")
            if todo and re.search(todo[0][0], out[seen:], re.I):
                seen = len(out)
                time.sleep(0.4)
                os.write(fd, (todo.pop(0)[1] + "\r").encode())
        else:
            out += "\n(gave up after %d seconds)" % timeout
    finally:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
        try:
            os.waitpid(pid, 0)
        except Exception:
            pass
        os.close(fd)
    return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", out)


def reset_immich(pw):
    new = friendly_password()
    say("    Asking CaciquePhotos' own admin tool for a new admin password (up to 90 seconds)...")
    out = run_with_terminal(["docker", "exec", "-it", "immich_server", "immich-admin", "reset-admin-password"],
                            [(r"new password", new), (r"Invalidate", "y")])
    email = (re.search(r"Email=(\S+)", out) or [None, None])[1]
    if "has been updated" not in out:
        say("    The tool didn't confirm the change.")
    if email and new and im_login(email, new)[0]:
        remember_reset(pw, "immich", email, new, email)
    else:
        say("    It didn't work. What immich-admin said: " + short(out, 400))


def reset_paperless(pw):
    if pl_make_elcacique(pw["elcacique"]["paperless"]):
        say("    El Cacique is ready in CaciqueDocs (your own account was not touched).")


def romm_sql(query):
    # the query goes in through stdin: password codes contain "$", which the shell would otherwise eat
    return sh(["docker", "exec", "-i", "caciquearcade-db", "sh", "-c",
               'mariadb -N -B -uroot -p"$MARIADB_ROOT_PASSWORD" romm'], inp=query + ";\n", timeout=60)


def romm_hash(password):
    for py in ("python3", "python", "/backend/.venv/bin/python", "/src/.venv/bin/python", "/.venv/bin/python"):
        rc, out = sh(["docker", "exec", "-e", "CQ_PW=" + password, "caciquearcade", py, "-c",
                      "import os,bcrypt;print(bcrypt.hashpw(os.environ['CQ_PW'].encode(),bcrypt.gensalt()).decode())"],
                     timeout=60)
        m = re.search(r"(\$2[aby]\$\d\d\$[./A-Za-z0-9]{53})", out)
        if m:
            return m.group(1)
    return None


def reset_romm(pw):
    rc, out = romm_sql("SELECT username FROM users WHERE role = 'admin' OR role = 'ADMIN'")
    names = [l.strip() for l in out.splitlines() if l.strip() and "Warning" not in l]
    if rc != 0 or not names:
        say("    Could not read the CaciqueArcade accounts: " + short(out, 300))
        return
    user = pick("Which CaciqueArcade admin should get a new password", names)
    if not user:
        say("    Skipped.")
        return
    new = friendly_password()
    h = romm_hash(new)
    if not h:
        say("    Could not make the password code inside CaciqueArcade.")
        return
    rc, out = romm_sql("UPDATE users SET hashed_password = '%s', enabled = 1 WHERE username = '%s'" % (h, user.replace("'", "")))
    if rc != 0:
        say("    It didn't work (database): " + short(out, 300))
    elif rm_token(user, new):
        remember_reset(pw, "romm", user, new, user)
    else:
        st, _, d = call(PORTS["romm"], "POST", "/api/token", form={
            "grant_type": "password", "username": user, "password": new, "scope": "users.read users.write"})
        say("    The new password is set, but CaciqueArcade said %s: %s" % (st, short(d, 200)))


def reset_homeassistant(pw):
    d = os.path.join(REPO_DIR, "homeassistant")
    base = ["docker", "compose", "run", "--rm", "--no-deps", "--entrypoint", "python", "homeassistant",
            "-m", "homeassistant", "--script", "auth", "--config", "/config"]
    say("    Stopping CaciqueHome for a moment...")
    sh(["docker", "compose", "stop"], cwd=d, timeout=120)
    try:
        rc, out = sh(base + ["list"], cwd=d, timeout=600)
        if rc != 0:
            say("    Could not read the CaciqueHome logins: " + short(out, 300))
            return
        names = [l.strip() for l in out.splitlines()
                 if l.strip() and not re.search(r"(?i)total|users|warning|error|creating|pulling|^\W", l)]
        user = pick("Which CaciqueHome login should get a new password", names)
        if not user:
            say("    Skipped." if names else "    Could not read the CaciqueHome logins: " + short(out, 300))
            return
        new = friendly_password()
        rc, out = sh(base + ["change_password", user, new], cwd=d, timeout=600)
        if "changed" in out.lower() or rc == 0:
            pw.setdefault("reset", {})["homeassistant"] = [user, new]
            save_json(os.path.join(ACC, "passwords.json"), pw)
            remember_reset(pw, "homeassistant", user, new, user)
        else:
            say("    It didn't work: " + short(out, 300))
    finally:
        say("    Starting CaciqueHome again...")
        sh(["docker", "compose", "up", "-d"], cwd=d, timeout=300)
        import time
        for _ in range(120):
            if is_up(PORTS["homeassistant"]):
                break
            time.sleep(2)


def reset_admins(pw, only=None):
    steps = [("jellyfin", reset_jellyfin), ("immich", reset_immich), ("paperless", reset_paperless),
             ("romm", reset_romm), ("homeassistant", reset_homeassistant)]
    for app, fn in steps:
        if only and app not in only:
            continue
        say("")
        say("== %s: admin access without the old password ==" % NAMES[app])
        if not is_up(PORTS[app]):
            say("    not running - skipped (start-all.sh first)")
            continue
        try:
            fn(pw)
        except Exception as e:
            say("    FAILED: %s: %s" % (e.__class__.__name__, short(str(e))))
    say("")
    say("  The new admin passwords are also saved (private) in: %s" % os.path.join(ACC, "new-admin-passwords.txt"))

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
    if "--set-admin" in sys.argv:
        return set_admin_login(people)
    set_admin(people)
    pw = load_passwords(people)
    ip = laptop_ip()
    say("  People: " + ", ".join("%s (%s)" % (p["nick"], p["type"]) for p in people))
    if "--reset-admins" in sys.argv:
        reset_admins(pw, only)
        say("")
        say("  Now making El Cacique and everyone's accounts with that access...")
    if "--fix-owners" in sys.argv:
        fix_owners(people, pw)
        say("")
        say("  Now making anything that's missing and refreshing the cards...")
    made = {}
    steps = [("jellyfin", lambda: do_jellyfin(people, pw)), ("immich", lambda: do_immich(people, pw, ip)),
             ("paperless", lambda: do_paperless(people, pw)), ("romm", lambda: do_romm(people, pw)),
             ("homeassistant", lambda: do_homeassistant(people, pw)), ("adguard", lambda: do_adguard(pw)),
             ("vaultwarden", lambda: do_vaultwarden(people))]
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
