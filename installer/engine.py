#!/usr/bin/env python3
"""
ElCaciqueDeck installer - the engine (no windows here; cacique_installer.py is the window).

  scan()            -> what this computer has (CPU, memory, disks, drives, network)
  check_levels(s)   -> which of the 3 levels this computer meets, and why not
  default_apps(...) -> the apps ticked by default for a level
  Installer(plan)   -> runs the install steps, one by one, reporting progress and every line of output

The three levels:
  1 Laptop  programs only, everything on the computer's own disk, no media. Baseline: the ThinkPad L540
            (4 threads, 8 GB memory; 8 GB laptops with built-in graphics show ~6 GB, which still counts).
  2 Deck    level 1 + at least one more drive (Library for media/games/cameras, Vault for documents/photos).
  3 Lab     the closet rig (docs/rig-shopping-list.md): 16 GB+ memory, 8+ threads, 2+ data drives,
            plus network gear (VLAN router/switch, UPS) checked by the person installing.

Every step is safe to run again: it checks first and keeps what's already there.
Test without touching the computer:  python3 installer/engine.py --dry-run
"""
import json, os, platform, pwd, re, shlex, shutil, socket, stat, subprocess, sys, tempfile, threading, time
import http.client, urllib.parse

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser("~")
USER = pwd.getpwuid(os.getuid()).pw_name
DATA = os.path.join(HOME, "elcaciquedeck-data")
CONF = os.path.join(DATA, "cacique.conf")
sys.path.insert(0, os.path.join(REPO, "accounts"))

LEVELS = {
    1: {"name": {"es": "Nivel 1 · Laptop", "en": "Level 1 · Laptop"},
        "desc": {"es": "Solo los programas, en el disco de esta computadora. Sin películas ni archivos grandes.",
                 "en": "Programs only, on this computer's own disk. No movies or big files."},
        "min_threads": 4, "min_ram": 5.5, "min_free": 40},
    2: {"name": {"es": "Nivel 2 · Deck", "en": "Level 2 · Deck"},
        "desc": {"es": "Nivel 1 + un disco más (Library y Vault) para películas, fotos, documentos y cámaras.",
                 "en": "Level 1 + another drive (Library and Vault) for movies, photos, documents and cameras."},
        "min_threads": 4, "min_ram": 5.5, "min_free": 40, "min_drives": 1, "min_drive_gb": 250},
    3: {"name": {"es": "Nivel 3 · Lab", "en": "Level 3 · Lab"},
        "desc": {"es": "El rig del closet: más memoria, 2+ discos, red con VLANs, firewall y UPS.",
                 "en": "The closet rig: more memory, 2+ drives, VLAN network, firewall and UPS."},
        "min_threads": 8, "min_ram": 15.0, "min_free": 100, "min_drives": 2, "min_drive_gb": 500},
}

# key, name, what it is (es, en), min level, folder with its setup (None = done by the engine), approx download GB
APPS = [
    ("names",    "CaciqueGuard",    "Nombres fáciles (.home) y bloqueo de anuncios", "Easy .home names and ad blocking", 1, 0.2),
    ("front",    "Cacique",         "La página de la familia (todos los botones)", "The family front page (every button)", 1, 0.2),
    ("library",  "CaciqueLibrary",  "Enciclopedia y Manual de Campo sin internet", "Offline encyclopedia and Field Manual", 1, 0.1),
    ("flix",     "CaciqueFlix",     "Películas y series de la casa (Jellyfin)", "The family's movies and shows (Jellyfin)", 1, 0.5),
    ("docs",     "CaciqueDocs",     "Documentos escaneados (Paperless)", "Scanned documents (Paperless)", 1, 1.0),
    ("photos",   "CaciquePhotos",   "Fotos y videos de la familia (Immich)", "Family photos and videos (Immich)", 1, 3.0),
    ("home",     "CaciqueHome",     "Casa inteligente: luces, sensores (Home Assistant)", "Smart home: lights, sensors (Home Assistant)", 1, 1.5),
    ("arcade",   "CaciqueArcade",   "Juegos legales en el navegador (RomM)", "Legal games in the browser (RomM)", 1, 1.0),
    ("vault",    "CaciqueVault",    "Caja fuerte de contraseñas (Vaultwarden)", "Password safe (Vaultwarden)", 1, 0.1),
    ("calendar", "CaciqueCalendar", "Calendario de la familia, en la casa (Radicale)", "Family calendar, kept at home (Radicale)", 1, 0.1),
    ("office",   "CaciqueOffice",   "LibreOffice en el navegador + archivos de cada uno (pesada: ~12 GB)", "LibreOffice in the browser + everyone's files (heavy: ~12 GB)", 1, 3.0),
    ("finanzas", "CaciqueFinanzas", "Presupuesto de la familia + coach con IA (Actual Budget)", "Family budget + AI money coach (Actual Budget)", 1, 0.4),
    ("sync",     "CaciqueSync",     "Nuestra propia Dropbox (Syncthing)", "Our own Dropbox (Syncthing)", 1, 0.05),
    ("guide",    "CaciqueGuía",     "IA local que ayuda a cuidar el Lab (Ollama)", "Local AI that helps care for the Lab (Ollama)", 1, 3.0),
    ("cams",     "CaciqueCams",     "Cámaras: graba aquí y borra a los 90 días (Frigate)", "Cameras: record here, delete after 90 days (Frigate)", 2, 1.5),
]
APP_KEYS = [a[0] for a in APPS]
# Heavy apps: only offered when the computer has this much memory (GB as Linux reports it; 16 GB shows ~15).
# They stay in GitHub, ready for a bigger Home Lab; "Show everything" on the apps page still allows them.
APP_MIN_RAM = {"office": 11.5}


def app_fits(key, s):
    return s.get("ram_gb", 0) >= APP_MIN_RAM.get(key, 0)


# ================================================================ looking at the computer
def sh_out(args, timeout=20):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout).stdout
    except Exception:
        return ""


def scan():
    s = {}
    osr = {}
    try:
        for line in open("/etc/os-release"):
            if "=" in line:
                k, v = line.rstrip().split("=", 1)
                osr[k] = v.strip('"')
    except Exception:
        pass
    s["os"] = osr.get("PRETTY_NAME", platform.platform())
    s["is_ubuntu"] = osr.get("ID") == "ubuntu" or "ubuntu" in osr.get("ID_LIKE", "")
    try:
        s["os_version"] = float(osr.get("VERSION_ID", "0"))
    except ValueError:
        s["os_version"] = 0.0
    s["arch"] = platform.machine()
    s["threads"] = os.cpu_count() or 1
    cpu = ""
    try:
        cpu = next((l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name")), "")
    except Exception:
        pass
    s["cpu"] = cpu or platform.processor() or "?"
    try:
        kb = int(next(l for l in open("/proc/meminfo") if l.startswith("MemTotal")).split()[1])
        s["ram_gb"] = round(kb / 1048576, 1)
    except Exception:
        s["ram_gb"] = 0.0
    st = os.statvfs(HOME)
    s["home_free_gb"] = round(st.f_bavail * st.f_frsize / 1e9, 1)
    s["home_total_gb"] = round(st.f_blocks * st.f_frsize / 1e9, 1)
    s["drives"] = list_drives()
    s["ip"] = laptop_ip()
    s["net_kind"] = network_kind()
    s["laptop"] = is_laptop()
    s["internet"] = can_reach("github.com", 443)
    s["docker"] = bool(shutil.which("docker"))
    s["gpu"] = " ".join(l for l in sh_out(["lspci"]).splitlines() if re.search(r"VGA|3D", l))[:200]
    s["existing"] = existing_install()
    return s


def list_drives():
    """Extra drives (not the system disk): mounted ones are ready to use."""
    try:
        data = json.loads(sh_out(["lsblk", "-J", "-b", "-o", "NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT,TYPE,TRAN,RM"]))
    except Exception:
        return []
    root_disk = None
    out = []

    def walk(devs, disk=None):
        nonlocal root_disk
        for d in devs:
            if d.get("type") == "disk":
                disk = d
            mp = d.get("mountpoint") or ""
            if mp in ("/", "/boot", "/boot/efi") or mp.startswith("/snap"):
                root_disk = (disk or {}).get("name")
            walk(d.get("children") or [], disk)

    walk(data.get("blockdevices", []))

    def collect(devs, disk=None):
        for d in devs:
            if d.get("type") == "disk":
                disk = d
            fs, mp = d.get("fstype") or "", d.get("mountpoint") or ""
            if (disk or {}).get("name") != root_disk and d.get("type") in ("part", "disk") and fs and fs != "swap" \
                    and not (d.get("type") == "disk" and d.get("children")):
                item = {"dev": "/dev/" + d["name"], "label": d.get("label") or "", "fstype": fs,
                        "size_gb": round(int(d.get("size") or 0) / 1e9), "mount": mp,
                        "usb": (disk or {}).get("tran") == "usb", "free_gb": None}
                if mp:
                    try:
                        st = os.statvfs(mp)
                        item["free_gb"] = round(st.f_bavail * st.f_frsize / 1e9)
                    except Exception:
                        pass
                out.append(item)
            collect(d.get("children") or [], disk)

    collect(data.get("blockdevices", []))
    # Second look: anything mounted under /media, /run/media or /mnt that lsblk didn't report (seen on Ubuntu 26.04)
    seen = {d["mount"] for d in out if d["mount"]}
    for line in sh_out(["findmnt", "-rn", "-t", "ext4,xfs,btrfs,f2fs,exfat,ntfs3,vfat", "-o", "TARGET,SOURCE,FSTYPE,LABEL"]).splitlines():
        parts = line.split(" ")
        if len(parts) < 3:
            continue
        target = parts[0].replace("\\x20", " ")
        if target in seen or not target.startswith(("/media/", "/run/media/", "/mnt/")):
            continue
        try:
            st = os.statvfs(target)
            size, free = st.f_blocks * st.f_frsize, st.f_bavail * st.f_frsize
        except Exception:
            continue
        out.append({"dev": parts[1], "label": parts[3].replace("\\x20", " ") if len(parts) > 3 else "", "fstype": parts[2],
                    "size_gb": round(size / 1e9), "mount": target, "usb": True, "free_gb": round(free / 1e9)})
        seen.add(target)
    return out


def laptop_ip():
    m = re.search(r"\bsrc (\S+)", sh_out(["ip", "route", "get", "1.1.1.1"]))
    return m.group(1) if m else ""


def can_reach(host, port):
    try:
        socket.create_connection((host, port), timeout=5).close()
        return True
    except Exception:
        return False


def existing_install():
    """What's already set up (an older ElCaciqueDeck, like the ThinkPad)."""
    found = []
    for key, path in [("names", "adguard/conf"), ("front", "homepage/.env"), ("docs", "paperless/.env"),
                      ("photos", "immich/.env"), ("home", "homeassistant/.env"), ("arcade", "arcade/.env"),
                      ("vault", "vaultwarden/.env"), ("calendar", "calendar/.env"), ("cams", "cameras/.env"), ("finanzas", "finanzas/.env"), ("office", "office/.env"),
                      ("guide", "guide/.env")]:
        if os.path.exists(os.path.join(REPO, path)):
            found.append(key)
    if shutil.which("flatpak") and "JellyfinServer" in sh_out(["flatpak", "list", "--app"]):
        found.append("flix")
    if os.path.exists(os.path.join(DATA, "sync.enabled")):
        found.append("sync")
    if shutil.which("kiwix-serve"):
        found.append("library")
    return found


# Program data a previous El Cacique left on the drives. Media (movies, games, encyclopedias, photos you copied)
# is never touched; only these program folders are set aside on a clean start.
OLD_APP_DATA = [("vault", "paperless"), ("vault", "vaultwarden"), ("vault", "Photos/immich"), ("vault", "calendar"), ("vault", "finanzas"), ("vault", "office"),
                ("vault", "Sync"), ("library", "Arcade/assets"), ("library", "Arcade/config"), ("library", "Cameras")]


def old_app_data(library, vault):
    found = []
    for where, rel in OLD_APP_DATA:
        path = os.path.join(vault if where == "vault" else library, rel)
        if os.path.isdir(path) and os.listdir(path):
            found.append(path)
    return found


def network_kind():
    """'ethernet', 'wifi' or '' - how this computer reaches the router."""
    m = re.search(r"\bdev (\S+)", sh_out(["ip", "route", "get", "1.1.1.1"]))
    if not m:
        return ""
    dev = m.group(1)
    if os.path.isdir("/sys/class/net/%s/wireless" % dev):
        return "wifi"
    return "ethernet"


def is_laptop():
    return any(os.path.exists(p) for p in ("/sys/class/power_supply/BAT0", "/sys/class/power_supply/BAT1"))


def usable_drives(s, min_gb):
    return [d for d in s["drives"] if d["mount"] and d["size_gb"] >= min_gb and d["fstype"] in
            ("ext4", "xfs", "btrfs", "f2fs")]


def check_levels(s):
    """{level: (ok, [reasons it doesn't fit])}"""
    res = {}
    for lv, req in LEVELS.items():
        why = []
        if not s["is_ubuntu"]:
            why.append(("Esta computadora no tiene Ubuntu", "This computer is not running Ubuntu"))
        elif s["os_version"] and s["os_version"] < 22.04:
            why.append(("Ubuntu %s es muy viejo (mínimo 22.04)" % s["os_version"], "Ubuntu %s is too old (22.04 or newer)" % s["os_version"]))
        if s["arch"] not in ("x86_64", "aarch64"):
            why.append(("Procesador %s no soportado" % s["arch"], "Processor %s not supported" % s["arch"]))
        if s["threads"] < req["min_threads"]:
            why.append(("Procesador: %d hilos (mínimo %d)" % (s["threads"], req["min_threads"]),
                        "Processor: %d threads (needs %d)" % (s["threads"], req["min_threads"])))
        if s["ram_gb"] < req["min_ram"]:
            need = 8 if req["min_ram"] < 8 else 16    # 8 GB computers often show ~6 GB: the graphics borrow the rest
            why.append(("Memoria: %.1f GB (mínimo %d GB)" % (s["ram_gb"], need),
                        "Memory: %.1f GB (needs %d GB)" % (s["ram_gb"], need)))
        if s["home_free_gb"] < req["min_free"]:
            why.append(("Espacio libre en el disco: %.0f GB (mínimo %d GB)" % (s["home_free_gb"], req["min_free"]),
                        "Free disk space: %.0f GB (needs %d GB)" % (s["home_free_gb"], req["min_free"])))
        if req.get("min_drives"):
            n = len(usable_drives(s, req["min_drive_gb"]))
            if n < req["min_drives"]:
                why.append(("Discos extra conectados (ext4, %d GB+): %d (mínimo %d)" % (req["min_drive_gb"], n, req["min_drives"]),
                            "Extra drives connected (ext4, %d GB+): %d (needs %d)" % (req["min_drive_gb"], n, req["min_drives"])))
        res[lv] = (not why, why)
    return res


def recommend(levels):
    best = 0
    for lv in (1, 2, 3):
        if levels[lv][0]:
            best = lv
    return best or 1


def default_apps(level, s):
    apps = {k for k, *_ in APPS}
    if level < 2:
        apps.discard("cams")
    if s["ram_gb"] < 11.5:
        apps.discard("guide")          # the AI is slow and heavy with 8 GB; can still be ticked
    for key in APP_MIN_RAM:
        if not app_fits(key, s):
            apps.discard(key)          # too heavy for this computer: not downloaded
    return apps


def guide_model(ram_gb):
    return "qwen2.5:14b" if ram_gb >= 30 else "qwen2.5:7b" if ram_gb >= 14 else "qwen2.5:3b"


# ================================================================ running the install
class Plan:
    def __init__(self):
        self.level = 1
        self.apps = set()
        self.library = os.path.join(DATA, "library")
        self.vault = os.path.join(DATA, "vault")
        self.vault_is_folder = True
        self.admin = "ElCaciqueAdmin"
        self.admin_pw = ""
        self.adults = []          # [(login, nickname)]
        self.family = True
        self.guest = True
        self.autostart = False
        self.lang = "es"
        self.sudo_pw = ""
        self.lab_checklist = {}
        self.clean_start = True     # set aside old program folders found on the drives (media is kept)
        self.server_mode = True     # never sleep on power, keep running with the lid closed, Wi-Fi without power saving

    def summary(self, lang="es"):
        es = lang == "es"
        rows = [(("Nivel", "Level"), LEVELS[self.level]["name"][lang]),
                (("Aplicaciones", "Apps"), ", ".join(a[1] for a in APPS if a[0] in self.apps)),
                (("Library (películas, juegos, cámaras)", "Library (movies, games, cameras)"), self.library),
                (("Vault (documentos, fotos, contraseñas)", "Vault (documents, photos, passwords)"), self.vault),
                (("Administrador", "Administrator"), self.admin),
                (("Adultos", "Adults"), ", ".join("%s (%s)" % (n, l) for l, n in self.adults) or "-"),
                (("Familia (PG) / Invitado (PG-13)", "Familia (PG) / Invitado (PG-13)"),
                 "%s / %s" % ("sí" if self.family else "no", "sí" if self.guest else "no") if es else
                 "%s / %s" % ("yes" if self.family else "no", "yes" if self.guest else "no")),
                (("Prender solo al encender", "Start by itself at power-on"), ("sí" if self.autostart else "no") if es else ("yes" if self.autostart else "no")),
                (("Modo servidor", "Server mode"), ("sí" if self.server_mode else "no") if es else ("yes" if self.server_mode else "no")),
                (("Empezar limpio en los discos", "Clean start on the drives"), ("sí" if self.clean_start else "no") if es else ("yes" if self.clean_start else "no"))]
        return [(k[0] if es else k[1], v) for k, v in rows]


class Stop(Exception):
    pass


class Installer:
    """Runs the steps. log(line) gets every line; progress(i, n, title) at each step."""

    def __init__(self, plan, log=print, progress=None, dry_run=False):
        self.p, self.progress, self.dry = plan, progress or (lambda *a: None), dry_run
        self.ip = laptop_ip() or "127.0.0.1"
        # every line also goes to reports/installer-<date>.txt, so a run can be checked afterwards
        self._file = None
        if not dry_run:
            try:
                os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
                self.log_path = os.path.join(REPO, "reports", "installer-%s.txt" % time.strftime("%Y-%m-%d_%H%M"))
                self._file = open(self.log_path, "a", encoding="utf-8")
            except Exception:
                self._file = None

        def both(line, _show=log):
            _show(line)
            if self._file:
                try:
                    self._file.write(line + "\n")
                    self._file.flush()
                except Exception:
                    pass
        self.log = both
        self.failed = []
        self.cancelled = threading.Event()
        self.tmp = tempfile.mkdtemp(prefix="cacique-install-")
        os.chmod(self.tmp, 0o700)
        self.env = dict(os.environ)
        self._sudo_setup()

    # ---------- sudo without a terminal: an "askpass" helper that hands sudo the password
    def _sudo_setup(self):
        pwf = os.path.join(self.tmp, "pw")
        with open(os.open(pwf, os.O_WRONLY | os.O_CREAT, 0o600), "w") as f:
            f.write(self.p.sudo_pw)
        ask = os.path.join(self.tmp, "askpass")
        with open(ask, "w") as f:
            f.write("#!/bin/sh\ncat %s\n" % shlex.quote(pwf))
        os.chmod(ask, stat.S_IRWXU)
        bindir = os.path.join(self.tmp, "bin")
        os.makedirs(bindir)
        wrapper = os.path.join(bindir, "sudo")
        with open(wrapper, "w") as f:
            f.write('#!/bin/sh\nexec /usr/bin/sudo -A "$@"\n')
        os.chmod(wrapper, stat.S_IRWXU)
        self.env.update(SUDO_ASKPASS=ask, PATH=bindir + ":" + self.env.get("PATH", "/usr/bin:/bin"),
                        DEBIAN_FRONTEND="noninteractive", CQ_ADMIN_USER=self.p.admin, CQ_ADMIN_PW=self.p.admin_pw)

    def cleanup(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---------- running things
    def run(self, cmd, cwd=None, check=True, docker=False, timeout=7200, env=None):
        """Run a command, showing every line. docker=True: make Docker usable even before the next login."""
        if self.cancelled.is_set():
            raise Stop()
        if docker and not self.docker_ok():
            cmd = self.as_docker_group(cmd)
        self.log("$ " + " ".join(shlex.quote(c) for c in cmd).replace(self.p.admin_pw or "\x00", "••••••"))
        if self.dry:
            return 0
        e = dict(self.env)
        e.update(env or {})
        proc = subprocess.Popen(cmd, cwd=cwd, env=e, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, text=True, errors="replace", bufsize=1)
        start = time.time()
        for line in proc.stdout:
            line = line.rstrip()
            if self.p.admin_pw:
                line = line.replace(self.p.admin_pw, "••••••")
            if self.p.sudo_pw:
                line = line.replace(self.p.sudo_pw, "••••••")
            self.log("  " + line)
            if self.cancelled.is_set():
                proc.terminate()
                raise Stop()
            if time.time() - start > timeout:
                proc.kill()
                raise RuntimeError("took longer than %d minutes" % (timeout // 60))
        rc = proc.wait()
        if check and rc != 0:
            raise RuntimeError("%s ended with error %d" % (cmd[-1].split()[0] if cmd[0] == "sg" or "-g" in cmd[:6] else os.path.basename(cmd[0]), rc))
        return rc

    def as_docker_group(self, cmd):
        """Run cmd with the 'docker' group even before the next login. Older Ubuntu: sg. Ubuntu 26.04 has no sg:
        sudo can switch the group (same user, same home)."""
        if shutil.which("sg"):
            return ["sg", "docker", "-c", shlex.join(cmd)]
        return ["sudo", "-A", "--preserve-env", "-u", USER, "-g", "docker", "bash", "-c", shlex.join(cmd)]

    def sudo(self, *args, **kw):
        return self.run(["sudo"] + list(args), **kw)

    def docker_ok(self):
        if self.dry:
            return True
        return subprocess.run(["docker", "info"], capture_output=True).returncode == 0

    def wait_port(self, port, seconds=180, path="/"):
        if self.dry:
            return True
        end = time.time() + seconds
        while time.time() < end:
            if self.cancelled.is_set():
                raise Stop()
            try:
                c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                c.request("GET", path)
                st = c.getresponse().status
                c.close()
                if st < 500:
                    return True
            except Exception:
                pass
            time.sleep(3)
        return False

    def http(self, port, method, path, body=None, headers=None, form=None):
        if self.dry:
            self.log("  [dry-run] %s :%d%s" % (method, port, path))
            return 200, {}
        h = {"Accept": "application/json"}
        h.update(headers or {})
        data = None
        if form is not None:
            data = urllib.parse.urlencode(form).encode()
            h["Content-Type"] = "application/x-www-form-urlencoded"
        elif body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
        try:
            c.request(method, path, body=data, headers=h)
            r = c.getresponse()
            raw = r.read()
            try:
                return r.status, json.loads(raw or b"null")
            except Exception:
                return r.status, raw.decode(errors="replace")
        finally:
            c.close()

    def script(self, rel, env=None):
        return self.run(["bash", os.path.join(REPO, rel)], cwd=REPO, docker=True, env=env)

    def logbook(self, level, msg):
        if not self.dry:
            subprocess.run([sys.executable, os.path.join(REPO, "tools", "logbook.py"), "add", "installer", level, msg],
                           capture_output=True)

    # ---------- the steps
    def steps(self):
        a, out = self.p.apps, []
        out.append((("Preparando", "Getting ready"), self.s_prepare))
        out.append((("Programas del sistema (Docker, etc.)", "System programs (Docker, etc.)"), self.s_packages))
        if self.p.server_mode:
            out.append((("Modo servidor (no dormir, tapa cerrada, Wi-Fi estable)", "Server mode (no sleep, lid closed, steady Wi-Fi)"),
                        self.s_server_mode))
        if "names" in a:
            out.append((("CaciqueGuard: nombres y anuncios", "CaciqueGuard: names and ads"), self.s_names))
        if "library" in a:
            out.append((("CaciqueLibrary", "CaciqueLibrary"), self.s_library))
        if "flix" in a:
            out.append((("CaciqueFlix", "CaciqueFlix"), self.s_flix))
        if "docs" in a:
            out.append((("CaciqueDocs", "CaciqueDocs"), lambda: self.script("paperless/setup-paperless.sh")))
        if "photos" in a:
            out.append((("CaciquePhotos", "CaciquePhotos"), self.s_photos))
        if "home" in a:
            out.append((("CaciqueHome", "CaciqueHome"), self.s_home))
        if "arcade" in a:
            out.append((("CaciqueArcade", "CaciqueArcade"), lambda: self.script("arcade/setup-arcade.sh")))
        if "vault" in a:
            out.append((("CaciqueVault", "CaciqueVault"), lambda: self.script("vaultwarden/setup-vault.sh")))
        if "calendar" in a:
            out.append((("CaciqueCalendar", "CaciqueCalendar"), lambda: self.script("calendar/setup-calendar.sh")))
        if "finanzas" in a:
            out.append((("CaciqueFinanzas", "CaciqueFinanzas"), lambda: self.script("finanzas/setup-finanzas.sh")))
        if "office" in a:
            out.append((("CaciqueOffice (descarga grande)", "CaciqueOffice (big download)"),
                        lambda: self.script("office/setup-office.sh",
                                            env={"CQ_FORCE": "0" if engine_fits("office") else "1"})))
        if "sync" in a:
            out.append((("CaciqueSync", "CaciqueSync"), self.s_sync))
        if "cams" in a:
            out.append((("CaciqueCams", "CaciqueCams"), lambda: self.script("cameras/setup-cameras.sh")))
        if "guide" in a:
            out.append((("CaciqueGuía (descarga grande)", "CaciqueGuía (big download)"),
                        lambda: self.script("guide/setup-guide.sh", env={"CQ_MODEL": guide_model(scan_ram())})))
        if "front" in a:
            out.append((("Página de la familia", "Family front page"), lambda: self.script("homepage/setup-homepage.sh")))
        out.append((("Cuentas (admin, adultos, Familia, Invitado)", "Accounts (admin, adults, Familia, Invitado)"), self.s_accounts))
        out.append((("Encender y accesos directos", "Power-on and shortcuts"), self.s_finish))
        return out

    def execute(self):
        steps = self.steps()
        self.logbook("info", "Installer started: level %d, apps %s" % (self.p.level, " ".join(sorted(self.p.apps))))
        try:
            for i, (title, fn) in enumerate(steps):
                t = title[0] if self.p.lang == "es" else title[1]
                self.progress(i, len(steps), t)
                self.log("")
                self.log("==== %d/%d  %s ====" % (i + 1, len(steps), t))
                try:
                    fn()
                    self.log("  [ OK ]  " + t)
                except Stop:
                    raise
                except Exception as e:
                    self.failed.append((t, str(e)))
                    self.log("  [FAIL]  %s: %s" % (t, e))
                    self.logbook("error", "Installer step failed: %s: %s" % (t, e))
                    if i < 2:          # without the basics nothing else can work
                        break
            self.progress(len(steps), len(steps), "")
        except Stop:
            self.log("  [STOP]  Cancelled")
            self.failed.append(("cancel", "cancelled"))
        finally:
            self.logbook("ok" if not self.failed else "warn",
                         "Installer finished: %d problems%s" % (len(self.failed), "" if not self.failed else
                                                               " (" + "; ".join(f[0] for f in self.failed) + ")"))
            self.cleanup()
        return not self.failed

    # ---------- individual steps
    def s_prepare(self):
        if not self.p.sudo_pw and not self.dry:
            raise RuntimeError("the computer password is needed")
        if not self.dry:
            r = subprocess.run(["sudo", "-A", "-v"], env=self.env, capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError("the computer password was not accepted")
        self.pin_drives()
        for d in (DATA, self.p.library, self.p.vault, os.path.join(self.p.library, "Kiwix")):
            self.log("  folder: " + d)
            if not self.dry:
                os.makedirs(d, exist_ok=True)
        conf = ["# ElCaciqueDeck settings - written by the installer (stays on this computer)",
                "CACIQUE_LEVEL=%d" % self.p.level,
                "LIBRARY=%s" % shlex.quote(self.p.library),
                "VAULT=%s" % shlex.quote(self.p.vault),
                "VAULT_IS_FOLDER=%d" % (1 if self.p.vault_is_folder else 0),
                "CACIQUE_APPS=%s" % shlex.quote(" ".join(sorted(self.p.apps))),
                "CACIQUE_AUTOSTART=%d" % (1 if self.p.autostart else 0),
                "CACIQUE_LANG=%s" % self.p.lang]
        self.log("  " + CONF)
        if not self.dry:
            with open(CONF, "w") as f:
                f.write("\n".join(conf) + "\n")
        if not self.p.vault_is_folder and not os.path.ismount(self.p.vault) and not self.dry:
            self.log("  [WARN] Vault is not a separate drive; using a folder")
        old = old_app_data(self.p.library, self.p.vault)
        if old and self.p.clean_start:
            stamp = time.strftime("%Y-%m-%d_%H%M")
            for path in old:
                base = self.p.vault if path.startswith(self.p.vault) else self.p.library
                dest = os.path.join(base, "_old-%s" % stamp, os.path.relpath(path, base))
                self.log("  clean start: %s -> %s (nothing deleted)" % (path, dest))
                if not self.dry:
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    r = subprocess.run(["sudo", "-A", "mv", path, dest], env=self.env, capture_output=True, text=True)
                    if r.returncode != 0:
                        raise RuntimeError("could not set aside %s: %s" % (path, r.stderr.strip()[:200]))
        elif old:
            self.log("  keeping the program data already on the drives: " + ", ".join(old))

    def pin_drives(self):
        """Ubuntu 26.04+ opens USB drives at /run/media/<user>/<name>, only after someone logs in.
        El Cacique wants them at /media/<user>/<name>, opened when the computer turns on: add them to /etc/fstab
        by their label ("nofail": the computer still starts if a drive is unplugged)."""
        for attr in ("library", "vault"):
            path = getattr(self.p, attr)
            if attr == "vault" and self.p.vault_is_folder:
                continue
            if not path.startswith("/run/media/"):
                continue
            src = sh_out(["findmnt", "-no", "SOURCE", path]).strip()
            label = sh_out(["lsblk", "-no", "LABEL", src]).strip() if src else ""
            fstype = sh_out(["lsblk", "-no", "FSTYPE", src]).strip() if src else ""
            if not label or not re.match(r"^[A-Za-z0-9_-]+$", label) or fstype not in ("ext4", "xfs", "btrfs", "f2fs"):
                self.log("  [WARN] %s: can't pin it to /media (label %r, type %r); using %s" % (attr, label, fstype, path))
                continue
            target = "/media/%s/%s" % (USER, label)
            line = "LABEL=%s %s %s defaults,nofail,x-gvfs-show 0 2" % (label, target, fstype)
            self.log("  %s drive: %s -> %s (opened at power-on)" % (attr, path, target))
            fstab = open("/etc/fstab").read() if os.path.exists("/etc/fstab") else ""
            if not re.search(r"^LABEL=%s\s" % re.escape(label), fstab, re.M):
                self.run(["bash", "-c", "printf '%%s\\n' %s | sudo tee -a /etc/fstab >/dev/null" % shlex.quote(line)])
            self.sudo("umount", path, check=False)
            self.sudo("mkdir", "-p", target)
            self.sudo("systemctl", "daemon-reload", check=False)
            self.sudo("mount", target)
            self.sudo("chown", "%s:%s" % (USER, USER), target)
            setattr(self.p, attr, target)

    def s_server_mode(self):
        """A home server must not fall asleep: no sleep on power, lid closed = keep running, Wi-Fi without power saving."""
        if is_laptop() or self.dry:
            conf = "[Login]\nHandleLidSwitch=ignore\nHandleLidSwitchExternalPower=ignore\nHandleLidSwitchDocked=ignore\n"
            self.run(["bash", "-c", "sudo mkdir -p /etc/systemd/logind.conf.d && printf %s | sudo tee "
                      "/etc/systemd/logind.conf.d/elcaciquedeck-lid.conf >/dev/null" % shlex.quote(conf)])
            self.log("  The lid can be closed: the server keeps running (takes effect after the next restart).")
        self.run(["bash", "-c", "printf '[connection]\\nwifi.powersave = 2\\n' | sudo tee "
                  "/etc/NetworkManager/conf.d/elcaciquedeck-wifi-powersave.conf >/dev/null"], check=False)
        for key, val in (("sleep-inactive-ac-type", "'nothing'"), ("sleep-inactive-ac-timeout", "0")):
            self.run(["gsettings", "set", "org.gnome.settings-daemon.plugins.power", key, val], check=False)
        self.sudo("systemctl", "mask", "sleep.target", "suspend.target", "hibernate.target", "hybrid-sleep.target", check=False)
        kind = network_kind()
        self.log("  Network: %s" % {"wifi": "Wi-Fi (works; a cable or USB network adapter is steadier for movies)",
                                     "ethernet": "cable (best)"}.get(kind, "not found"))

    def s_packages(self):
        pk = ["curl", "git", "openssl", "python3-bcrypt", "ufw", "sqlite3", "docker.io", "docker-compose-v2"]
        if "flix" in self.p.apps:
            pk.append("flatpak")
        if "library" in self.p.apps:
            pk.append("kiwix-tools")
        if "sync" in self.p.apps:
            pk.append("syncthing")
        missing = [p for p in pk if subprocess.run(["dpkg", "-s", p], capture_output=True).returncode != 0] if not self.dry else pk
        if missing:
            self.sudo("apt-get", "-o", "DPkg::Lock::Timeout=600", "update", "-q")
            self.sudo("apt-get", "-o", "DPkg::Lock::Timeout=600", "install", "-y", "-q", *missing)
        else:
            self.log("  all system programs already installed")
        self.sudo("systemctl", "enable", "--now", "docker", check=False)
        groups = sh_out(["id", "-nG", USER]).split()
        if "docker" not in groups:
            self.sudo("usermod", "-aG", "docker", USER)
            self.log("  You were added to the 'docker' group (works fully after the next restart).")
        if not self.dry and not self.docker_ok() and subprocess.run(self.as_docker_group(["docker", "info"]), env=self.env,
                                                                    capture_output=True).returncode != 0:
            raise RuntimeError("Docker is installed but not answering")

    def s_names(self):
        self.script("adguard/setup-adguard.sh")
        # AdGuard's first-time wizard, done for you: admin login + .home names for every device
        st, d = self.http(3000, "GET", "/control/install/get_addresses")
        if st == 200:
            st, d = self.http(3000, "POST", "/control/install/configure", {
                "web": {"ip": "0.0.0.0", "port": 3000, "status": "", "can_autofix": False},
                "dns": {"ip": "0.0.0.0", "port": 53, "status": "", "can_autofix": False},
                "username": self.p.admin, "password": self.p.admin_pw})
            self.log("  AdGuard first-time setup: %s" % ("done" if st == 200 else "answer %s %s" % (st, str(d)[:200])))
            self.wait_port(3000, 60)
        import base64
        auth = {"Authorization": "Basic " + base64.b64encode(("%s:%s" % (self.p.admin, self.p.admin_pw)).encode()).decode()}
        st, rw = self.http(3000, "GET", "/control/rewrite/list", headers=auth)
        if st == 200 and not any(r.get("domain") == "*.home" for r in (rw or [])):
            st, d = self.http(3000, "POST", "/control/rewrite/add", {"domain": "*.home", "answer": self.ip}, headers=auth)
            self.log("  *.home -> %s: %s" % (self.ip, "added" if st == 200 else st))
        elif st != 200:
            self.log("  [WARN] Could not log in to CaciqueGuard as %s (an older setup keeps its own login)" % self.p.admin)

    def s_library(self):
        z = os.path.join(REPO, "manual", "dist", "elcaciquedeck-manual.zim")
        dest = os.path.join(self.p.library, "Kiwix", "elcaciquedeck-manual.zim")
        self.log("  Field Manual -> " + dest)
        if not self.dry and os.path.exists(z):
            shutil.copy2(z, dest)
        self.run(["bash", "-c", "sudo ufw status | grep -q 'Status: active' && sudo ufw allow 8080/tcp || true"])

    def s_flix(self):
        if "JellyfinServer" not in sh_out(["flatpak", "list", "--app"]):
            self.run(["flatpak", "remote-add", "--user", "--if-not-exists", "flathub",
                      "https://flathub.org/repo/flathub.flatpakrepo"])
            self.run(["flatpak", "install", "--user", "-y", "--noninteractive", "flathub", "org.jellyfin.JellyfinServer"])
        self.run(["bash", "-c", "sudo ufw status | grep -q 'Status: active' && sudo ufw allow 8096/tcp || true"])
        if not self.wait_port(8096, 5):
            self.run(["bash", "-c", "mkdir -p %s && setsid nohup flatpak run org.jellyfin.JellyfinServer >%s 2>&1 &" %
                      (shlex.quote(os.path.join(REPO, "reports", "run")),
                       shlex.quote(os.path.join(REPO, "reports", "run", "jellyfin.log")))])
        if not self.wait_port(8096, 240, "/System/Info/Public"):
            raise RuntimeError("CaciqueFlix did not start")
        st, info = self.http(8096, "GET", "/System/Info/Public")
        if isinstance(info, dict) and info.get("StartupWizardCompleted"):
            self.log("  CaciqueFlix was already set up - keeping it (the accounts step adds the admin)")
            return
        self.log("  CaciqueFlix first-time setup (done for you)")
        self.http(8096, "POST", "/Startup/Configuration", {"UICulture": "es", "MetadataCountryCode": "US",
                                                          "PreferredMetadataLanguage": "es"})
        self.http(8096, "GET", "/Startup/User")
        self.http(8096, "POST", "/Startup/User", {"Name": self.p.admin, "Password": self.p.admin_pw})
        self.http(8096, "POST", "/Startup/RemoteAccess", {"EnableRemoteAccess": True, "EnableAutomaticPortMapping": False})
        st, _ = self.http(8096, "POST", "/Startup/Complete")
        self.log("  wizard: %s" % ("done" if st in (200, 204) else st))
        # the libraries: folders on Library
        from create_accounts import jf_auth, call as acall      # same helpers as the accounts tool
        if self.dry:
            return
        st, _, d = acall(8096, "POST", "/Users/AuthenticateByName", {"Username": self.p.admin, "Pw": self.p.admin_pw}, jf_auth())
        if st != 200:
            self.log("  [WARN] Could not log in to add the libraries (add them in CaciqueFlix -> Dashboard -> Libraries)")
            return
        H = jf_auth(d["AccessToken"])
        for folder, ctype, label in [("Movies", "movies", "Películas · Movies"), ("Shows", "tvshows", "Series · Shows"),
                                     ("Music", "music", "Música · Music")]:
            path = os.path.join(self.p.library, folder)
            os.makedirs(path, exist_ok=True)
            q = urllib.parse.urlencode({"name": label, "collectionType": ctype, "refreshLibrary": "false"})
            st, _, _ = acall(8096, "POST", "/Library/VirtualFolders?" + q,
                             {"LibraryOptions": {"PathInfos": [{"Path": path}]}}, H)
            self.log("  library %s -> %s (%s)" % (label, path, st))

    def s_photos(self):
        self.script("immich/setup-immich.sh")
        email = "%s@cacique.home" % self.p.admin.lower()
        st, d = self.http(2283, "POST", "/api/auth/admin-sign-up",
                          {"email": email, "password": self.p.admin_pw, "name": self.p.admin})
        self.log("  admin %s: %s" % (email, "created" if st in (200, 201) else "already set up (%s)" % st))

    def s_home(self):
        self.script("homeassistant/setup-homeassistant.sh")
        if self.dry:
            return
        import create_accounts as ca
        self.wait_port(8123, 240)
        tok = ca.ha_onboard_owner(self.p.admin, self.p.admin.lower(), self.p.admin_pw)
        self.log("  owner %s: %s" % (self.p.admin.lower(), "created" if tok else "already set up"))

    def s_sync(self):
        flag = os.path.join(DATA, "sync.enabled")
        folder = os.path.join(self.p.vault, "Sync")
        if not self.dry:
            os.makedirs(folder, exist_ok=True)
            open(flag, "w").write("on\n")
        for port, proto in (("8384", "tcp"), ("22000", "tcp"), ("22000", "udp"), ("21027", "udp")):
            self.run(["bash", "-c", "sudo ufw status | grep -q 'Status: active' && sudo ufw allow %s/%s || true" % (port, proto)])
        if not self.wait_port(8384, 3):
            self.run(["bash", "-c", "setsid nohup syncthing serve --no-browser --gui-address=0.0.0.0:8384 >%s 2>&1 &" %
                      shlex.quote(os.path.join(DATA, "syncthing.log"))])
        self.wait_port(8384, 90)
        self.run(["syncthing", "cli", "config", "gui", "user", "set", self.p.admin], check=False)
        self.run(["syncthing", "cli", "config", "gui", "password", "set", self.p.admin_pw], check=False)
        self.run(["syncthing", "cli", "config", "folders", "add", "--id", "cacique-sync", "--label", "Cacique Sync",
                  "--path", folder], check=False)

    def s_accounts(self):
        acc = os.path.join(DATA, "accounts")
        self.log("  people: %s, Familia, Invitado, %s" % (self.p.admin, ", ".join(n for _, n in self.p.adults) or "-"))
        if self.dry:
            return
        os.makedirs(acc, mode=0o700, exist_ok=True)
        lines = ["# ElCaciqueDeck - people with accounts (stays on this laptop)",
                 "# login|nickname|type   (type: admin, adult, family, guest)",
                 "%s|%s|admin" % (self.p.admin.lower(), self.p.admin)]
        if self.p.family:
            lines.append("familia|Familia|family")
        if self.p.guest:
            lines.append("invitado|Invitado|guest")
        keep = []
        path = os.path.join(acc, "people.txt")
        if os.path.exists(path):        # keep adults added before (by people.sh)
            for l in open(path, encoding="utf-8").read().splitlines():
                if l.endswith("|adult") and l.split("|")[0] not in [a for a, _ in self.p.adults]:
                    keep.append(l)
        lines += keep + ["%s|%s|adult" % (l, n) for l, n in self.p.adults]
        with open(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        import create_accounts as ca
        ca.ACC = acc
        people = ca.load_people()
        pw = ca.load_passwords(people)
        for app in ("jellyfin", "immich", "paperless", "romm", "homeassistant", "adguard", "calendar", "cams"):
            pw["elcacique"][app] = self.p.admin_pw
        pw["elcacique"]["office"] = self.p.admin_pw
        ca.save_json(os.path.join(acc, "passwords.json"), pw)
        self.script("accounts/create-accounts.sh")

    def s_finish(self):
        unit = "/etc/systemd/system/elcaciquedeck.service"
        if self.p.autostart:
            text = ("[Unit]\nDescription=ElCaciqueDeck - start the Home Lab servers\n"
                    "After=network-online.target docker.service\nWants=network-online.target\n\n"
                    "[Service]\nType=oneshot\nRemainAfterExit=yes\nUser=%s\nEnvironment=HOME=%s\n"
                    "ExecStart=/bin/bash %s/start-all.sh\nTimeoutStartSec=900\n\n"
                    "[Install]\nWantedBy=multi-user.target\n" % (USER, HOME, REPO))
            self.run(["bash", "-c", "printf %s | sudo tee " % shlex.quote(text) + unit + " >/dev/null"])
            self.sudo("systemctl", "daemon-reload")
            self.sudo("systemctl", "enable", "elcaciquedeck.service")
            self.log("  The servers will start by themselves when the computer turns on.")
        elif os.path.exists(unit):
            self.sudo("systemctl", "disable", "elcaciquedeck.service", check=False)
            self.log("  Start-by-itself is OFF (use start-all.sh).")
        # the gauges are always on, so the owner can watch the Home Lab while other servers stop/update
        self.run(["bash", os.path.join(REPO, "tools", "dash-always-on.sh")], check=False)
        # menu shortcuts
        apps = os.path.join(HOME, ".local", "share", "applications")
        icon = os.path.join(REPO, "homepage", "custom-icons", "cacique-emblem.svg")
        entries = {
            "elcaciquedeck-setup.desktop": ("El Cacique Setup", "Instalar o cambiar El Cacique Home Lab",
                                            "%s %s/installer/cacique_installer.py" % (shutil.which("python3") or "python3", REPO)),
            "elcaciquedeck.desktop": ("El Cacique", "Abrir la página de la familia", "xdg-open http://%s" % self.ip),
        }
        for name, (title, comment, cmd) in entries.items():
            self.log("  menu: " + title)
            if not self.dry:
                os.makedirs(apps, exist_ok=True)
                with open(os.path.join(apps, name), "w") as f:
                    f.write("[Desktop Entry]\nType=Application\nName=%s\nComment=%s\nExec=%s\nIcon=%s\nTerminal=false\n"
                            "Categories=Utility;\n" % (title, comment, cmd, icon))
        self.run(["bash", os.path.join(REPO, "start-all.sh")], docker=True, check=False)
        self.run([sys.executable, os.path.join(REPO, "tools", "logbook.py"), "collect"], check=False)


def engine_fits(key):
    return scan_ram() >= APP_MIN_RAM.get(key, 0)


def scan_ram():
    try:
        return int(next(l for l in open("/proc/meminfo") if l.startswith("MemTotal")).split()[1]) / 1048576
    except Exception:
        return 8


if __name__ == "__main__":
    s = scan()
    print(json.dumps(s, indent=1))
    lv = check_levels(s)
    for k, (ok, why) in lv.items():
        print("Level", k, "OK" if ok else "no:", "; ".join(w[1] for w in why))
    if "--dry-run" in sys.argv:
        p = Plan()
        p.level = recommend(lv)
        p.apps = default_apps(p.level, s)
        p.admin_pw, p.adults = "admin123", [("maria", "Mari")]
        ins = Installer(p, dry_run=True)
        ok = ins.execute()
        print("dry-run finished:", "ok" if ok else ins.failed)
