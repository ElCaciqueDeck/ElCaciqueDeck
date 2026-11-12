#!/usr/bin/env bash
# ElCaciqueDeck - show the Home Lab's passwords, organized for writing them in your notebook
#
#   bash ~/elcaciquedeck/tools/show-passwords.sh --admin     1. El Cacique's admin logins (every app)
#   bash ~/elcaciquedeck/tools/show-passwords.sh --people    2. each adult's starter password and where it works
#   bash ~/elcaciquedeck/tools/show-passwords.sh --other     3. the rest: Diario, Vault admin key, budget, links
#   bash ~/elcaciquedeck/tools/show-passwords.sh             all three
#
# It only READS the private files in ~/elcaciquedeck-data (nothing is changed, nothing goes online).
# Don't photograph the screen. Once everything is in your notebook (and later in CaciqueVault), you can delete
# the starter-password files with:  bash ~/elcaciquedeck/accounts/people.sh forget-passwords
python3 - "$@" <<'PY'
import csv, json, os, subprocess, sys

HOME = os.path.expanduser("~")
DATA = os.path.join(HOME, "elcaciquedeck-data")
ACC = os.path.join(DATA, "accounts")
REPO = os.path.join(HOME, "elcaciquedeck")
want = {a.strip("-") for a in sys.argv[1:]} or {"admin", "people", "other"}
NAMES = {"jellyfin": "CaciqueFlix", "immich": "CaciquePhotos", "paperless": "CaciqueDocs", "romm": "CaciqueArcade",
         "homeassistant": "CaciqueHome", "adguard": "CaciqueGuard", "calendar": "CaciqueCalendar", "cams": "CaciqueCams",
         "office": "CaciqueOffice"}
PORTS = {"jellyfin": ":8096", "immich": ":2283", "paperless": ":8000", "romm": ":8090", "homeassistant": ":8123",
         "adguard": ":3000", "calendar": ":5232", "cams": ":8971", "office": ":5445 (https)"}


def read(path, default=""):
    try:
        return open(path, encoding="utf-8").read().strip()
    except Exception:
        return default


def ip():
    try:
        out = subprocess.run(["ip", "-4", "-o", "addr", "show", "scope", "global"], capture_output=True, text=True).stdout
        for line in out.splitlines():
            f = line.split()
            if not f[1].startswith(("docker", "br-", "veth", "virbr", "lo")):
                return f[3].split("/")[0]
    except Exception:
        pass
    return "<server>"


def installed(app):
    marks = {"jellyfin": None, "immich": "immich/.env", "paperless": "paperless/.env", "romm": "arcade/.env",
             "homeassistant": "homeassistant/.env", "adguard": "adguard/conf", "calendar": "calendar/.env",
             "cams": "cameras/.env", "office": "office/.env"}
    m = marks.get(app)
    return True if m is None else os.path.exists(os.path.join(REPO, m))


def line(n, label, value):
    print("  %-3s %-28s %s" % (n, label, value))


people = []
for l in read(os.path.join(ACC, "people.txt")).splitlines():
    if l.strip() and not l.startswith("#") and l.count("|") == 2:
        login, nick, kind = l.split("|")
        people.append({"login": login, "nick": nick, "type": kind, "email": login + "@cacique.home"})
try:
    pw = json.load(open(os.path.join(ACC, "passwords.json")))
except Exception:
    pw = {}
HOST = ip()
print()
print("  EL CACIQUE · LIBRETA DE CONTRASEÑAS / PASSWORD NOTEBOOK")
print("  Casa / Home: http://%s      (escribe todo exactamente: mayúsculas cuentan / capitals count)" % HOST)

if not people:
    print("\n  No people list yet (~/elcaciquedeck-data/accounts/people.txt). Run the installer or accounts/people.sh first.")
    sys.exit(0)

if "admin" in want:
    ad = next((p for p in people if p["type"] == "admin"), None)
    print("\n  1. ADMINISTRADOR / ADMIN  -  %s" % (ad["nick"] if ad else "?"))
    print("  " + "-" * 74)
    if not ad:
        print("  No admin line in people.txt.")
    else:
        login = {"jellyfin": ad["nick"], "immich": ad["email"], "paperless": ad["nick"], "romm": ad["login"],
                 "homeassistant": ad["login"], "adguard": ad["nick"], "calendar": ad["login"], "cams": ad["login"],
                 "office": ad["login"]}
        # the import file has the exact login each app accepted
        try:
            for r in csv.DictReader(open(os.path.join(ACC, "for-vaultwarden-import.csv"), encoding="utf-8")):
                for app, name in NAMES.items():
                    if r.get("name", "").endswith(name) and r.get("login_username"):
                        login[app] = r["login_username"]
        except Exception:
            pass
        mine = pw.get("elcacique", {})
        same = len({mine.get(a) for a in NAMES if installed(a) and mine.get(a)}) == 1
        n = 0
        for app, name in NAMES.items():
            if not installed(app) or not mine.get(app):
                continue
            n += 1
            print("  %d) %-15s http://%s%s" % (n, name, HOST, PORTS[app]))
            print("       usuario / login:     %s" % login[app])
            if not same:
                print("       contraseña / pass:   %s" % mine[app])
            reset = pw.get("reset", {}).get(app)
            if reset:
                print("       (reseteada / reset:  %s  /  %s)" % (reset[0], reset[1]))
        if same and n:
            print("\n  Misma contraseña en todas / Same password in all of them:   %s" % next(mine[a] for a in NAMES if installed(a) and mine.get(a)))
        if not n:
            print("  No admin passwords saved yet: the accounts step hasn't run (bash ~/elcaciquedeck/accounts/create-accounts.sh).")

if "people" in want:
    adults = [p for p in people if p["type"] == "adult"]
    print("\n  2. ADULTOS / ADULTS  (contraseña inicial: cada uno la cambia al entrar / starter: each one changes it)")
    print("  " + "-" * 74)
    if not adults:
        print("  No adults on the list yet.")
    for p in adults:
        print("  %-14s login: %-14s correo/email: %-28s inicial/starter: %s" % (
            p["nick"], p["login"], p["email"], pw.get("people", {}).get(p["login"], "(todavía no / not yet)")))
        card = read(os.path.join(ACC, "cards", p["login"] + ".txt"))
        if not card:
            print("                 (sin cuentas todavía / no accounts yet: run accounts/create-accounts.sh)")
    print("\n  ¿Falta alguien (por ejemplo tú)? / Someone missing (you?):")
    print("    bash ~/elcaciquedeck/accounts/people.sh add <login> <Apodo>     then:  bash ~/elcaciquedeck/accounts/create-accounts.sh")
    for p in people:
        if p["type"] in ("family", "guest"):
            print("  %-14s sin contraseña / no password (%s)" % (p["nick"], "toca y entra / tap to enter"))

if "other" in want:
    print("\n  3. OTROS / OTHER")
    print("  " + "-" * 74)
    items = [("Cacique Diario (adultos)", "http://%s:8097/admin" % HOST, read(os.path.join(ACC, "diario-password.txt"))),
             ("Llave del Diario / Diario key", "(papel o USB en la caja fuerte / paper or USB in the safe)",
              read(os.path.join(DATA, "keys", "diario.key"))),
             ("CaciqueVault /admin key", "https://%s:8443/admin" % HOST, read(os.path.join(ACC, "vaultwarden-admin-token.txt"))),
             ("CaciqueFinanzas", "https://%s:5443" % HOST, read(os.path.join(ACC, "finanzas-password.txt"))),
             ("Familia Abierta (link)", "", read(os.path.join(ACC, "open-photos-link.txt")))]
    n = 0
    for label, where, value in items:
        if value:
            n += 1
            print("  %d) %s  %s" % (n, label, where))
            print("       %s" % value)
    if not n:
        print("  Nothing else saved yet.")
print()
print("  No le tomes foto a esta pantalla. / Don't photograph this screen.")
print()
PY
