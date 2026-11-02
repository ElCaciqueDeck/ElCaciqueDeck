#!/usr/bin/env python3
"""
ElCaciqueDeck - take a "photo" of the deck for El Cacique Admin (CaciqueAcademy 2.0).

Run by tools/snapshot.sh (which update.sh calls at the end). You can also run it alone:
    bash ~/elcaciquedeck/tools/snapshot.sh

It saves, ONLY on this laptop:
    ~/elcaciquedeck-data/twin/<date_time>/snapshot.json   (folders, drives, servers, command outputs)
    ~/elcaciquedeck-data/twin/<date_time>/screenshots/    (a picture of each Cacique page)
    ~/elcaciquedeck-data/twin/latest  -> the newest one
    ~/elcaciquedeck-data/twin/index.json (list of all snapshots, for the time machine)

Privacy rules (checked by the tests):
  * No file CONTENTS are read, except the .env settings files, and in those every
    password / key / secret / token is replaced with ••••••.
  * The Vault drive is private: only its top folders with a file count and total size.
    No document or photo names.
  * Your home folder: only the top folder names.
  * Nothing here is ever uploaded to GitHub (the folder is outside the repo).
"""
import datetime, json, os, re, shutil, socket, subprocess, sys, time
import http.client

HOME = os.path.expanduser("~")
USER = os.environ.get("USER") or os.path.basename(HOME)
REPO = os.environ.get("REPO") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBRARY = os.environ.get("LIBRARY") or "/media/%s/Library" % USER
VAULT = os.environ.get("VAULT") or "/media/%s/Vault" % USER
TWIN = os.environ.get("TWIN_DIR") or os.path.join(HOME, "elcaciquedeck-data", "twin")
KEEP = 20                      # how many snapshots to keep
MASK = "••••••"

SERVICES = [  # key, name, port, address name
    ("front", "Cacique", 80, "cacique.home"),
    ("library", "CaciqueLibrary", 8080, "caciquelibrary.home"),
    ("flix", "CaciqueFlix", 8096, "caciqueflix.home"),
    ("docs", "CaciqueDocs", 8000, "caciquedocs.home"),
    ("photos", "CaciquePhotos", 2283, "caciquephotos.home"),
    ("home", "CaciqueHome", 8123, "caciquehome.home"),
    ("arcade", "CaciqueArcade", 8090, "caciquearcade.home"),
    ("academy", "CaciqueAcademy", 8095, "caciqueacademy.home"),
    ("dash", "CaciqueDash", 8888, "caciquedash.home"),
    ("guard", "CaciqueGuard", 3000, "caciqueguard.home"),
]
SECRET_KEY = re.compile(r"(PASS|SECRET|KEY|TOKEN|PWD|SALT|CREDENTIAL)", re.I)
SECRET_INLINE = re.compile(r"(?i)\b([\w.-]*(?:password|passwd|secret|token|api[_-]?key)[\w.-]*)(\s*[=:]\s*)(\S+)")
SKIP_REPO = {".git", "reports", "manual/site", "homepage/icons", "homepage/config/logs"}
PRIVATE_REPO = {"adguard/conf", "adguard/work"}   # AdGuard's own settings (has a password hash)

warnings = []


def warn(msg):
    warnings.append(msg)
    print("  [WARN]  " + msg)


def mask_text(text):
    return SECRET_INLINE.sub(lambda m: m.group(1) + m.group(2) + MASK, text or "")


def run(cmd, timeout=20):
    """Run a command, return what it printed (masked). Never crashes."""
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout,
                           env=dict(os.environ, LC_ALL="C", LANG="C"))
        out = p.stdout
        if p.returncode != 0 and p.stderr.strip():
            out = (out + p.stderr).strip() + "\n"
        return mask_text(out.rstrip("\n"))
    except Exception as e:  # missing command, timeout...
        return "(could not run: %s)" % e.__class__.__name__


def http_code(port):
    try:
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=4)
        c.request("GET", "/")
        code = c.getresponse().status
        c.close()
        return code
    except Exception:
        return 0


# ---------------------------------------------------------------- folders
def tree(path, depth, max_entries=300, rel="", private_rel=()):
    """Folder tree: names and sizes only, never file contents."""
    node = {"n": os.path.basename(path.rstrip("/")) or path, "d": 1, "c": []}
    try:
        entries = sorted(os.scandir(path), key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()))
    except Exception:
        node["e"] = 1   # couldn't open
        return node
    shown = 0
    for e in entries:
        r = (rel + "/" + e.name).lstrip("/")
        if path.startswith(REPO) and r in SKIP_REPO:
            continue
        if e.name in ("__pycache__", ".git", "node_modules"):
            continue
        if shown >= max_entries:
            node["t"] = len(entries) - shown
            break
        shown += 1
        try:
            if e.is_dir(follow_symlinks=False):
                if r in private_rel:
                    node["c"].append(dict(summary(e.path), n=e.name))
                elif depth > 1:
                    node["c"].append(tree(e.path, depth - 1, max_entries, r, private_rel))
                else:
                    child = {"n": e.name, "d": 1, "c": [], "more": 1}
                    node["c"].append(child)
            else:
                node["c"].append({"n": e.name, "s": e.stat(follow_symlinks=False).st_size})
        except Exception:
            continue
    return node


def summary(path, limit_s=20):
    """A private folder: only how many files and how big. No names."""
    count = size = 0
    start = time.time()
    for root, dirs, files in os.walk(path):
        for f in files:
            try:
                size += os.lstat(os.path.join(root, f)).st_size
                count += 1
            except Exception:
                pass
        if time.time() - start > limit_s:
            break
    return {"n": os.path.basename(path), "d": 1, "p": 1, "k": count, "s": size}


def vault_tree():
    if not os.path.isdir(VAULT) or not os.listdir(VAULT):
        return None
    node = {"n": "Vault", "d": 1, "c": []}
    for e in sorted(os.scandir(VAULT), key=lambda e: e.name.lower()):
        if e.name.startswith(".") or e.name == "lost+found":
            continue
        if e.is_dir(follow_symlinks=False):
            node["c"].append(summary(e.path))
        else:
            node["c"].append({"n": "(1 file)", "p": 1, "s": e.stat().st_size})
    return node


def home_tree():
    node = {"n": USER, "d": 1, "c": []}
    for e in sorted(os.scandir(HOME), key=lambda e: e.name.lower()):
        if e.name.startswith("."):
            continue
        p = os.path.realpath(e.path)
        if p == os.path.realpath(REPO):
            continue   # shown in full separately
        if e.is_dir():
            node["c"].append({"n": e.name, "d": 1, "c": [], "p": 1})
    return node


def env_files():
    out = {}
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if os.path.relpath(os.path.join(root, d), REPO) not in SKIP_REPO | PRIVATE_REPO]
        for f in files:
            if f == ".env" or f.endswith(".env"):
                path = os.path.join(root, f)
                lines = []
                try:
                    for line in open(path, errors="replace"):
                        line = line.rstrip("\n")
                        m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)", line)
                        if m and SECRET_KEY.search(m.group(1)):
                            line = m.group(1) + "=" + MASK
                        lines.append(mask_text(line))
                except Exception:
                    lines = ["(could not read)"]
                out[os.path.relpath(path, REPO)] = "\n".join(lines)
    return out


# ---------------------------------------------------------------- drives
def drives():
    result = []
    try:
        data = json.loads(run("lsblk -J -b -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT,TYPE,RM,TRAN"))
    except Exception:
        return result

    def walk(devs, disk=None):
        for d in devs:
            if d.get("type") == "disk":
                disk = d
            fs, mp = d.get("fstype") or "", d.get("mountpoint") or ""
            skip = d.get("type") == "loop" or fs in ("swap", "squashfs") or mp.startswith(("/snap", "/boot"))
            if not skip and (fs or mp):
                item = {"device": "/dev/" + d["name"], "label": d.get("label") or "", "fstype": fs,
                        "size": int(d.get("size") or 0), "mount": mp, "usb": (disk or {}).get("tran") == "usb"}
                if mp:
                    try:
                        st = os.statvfs(mp)
                        item["used"] = (st.f_blocks - st.f_bfree) * st.f_frsize
                        item["avail"] = st.f_bavail * st.f_frsize
                        item["total"] = st.f_blocks * st.f_frsize
                    except Exception:
                        pass
                result.append(item)
            walk(d.get("children") or [], disk)
    walk(data.get("blockdevices", []))
    return result


# ---------------------------------------------------------------- screenshots
def screenshots(dest, services):
    ff = shutil.which("firefox")
    if not ff:
        warn("Firefox not found - no screenshots this time")
        return {}
    os.makedirs(dest, exist_ok=True)
    # outside the twin folder (which the Academy serves); not hidden: the Ubuntu (snap) Firefox can't use hidden folders
    profile = os.path.join(os.path.dirname(TWIN.rstrip("/")), "twin-firefox-profile")
    os.makedirs(profile, exist_ok=True)
    shots = {}
    for s in services:
        if not s["up"]:
            continue
        out = os.path.join(dest, s["key"] + ".png")
        url = "http://127.0.0.1:%d/" % s["port"]
        try:
            subprocess.run([ff, "--headless", "--no-remote", "--profile", profile,
                            "--window-size=1280,800", "--screenshot", out, url],
                           capture_output=True, timeout=60)
        except Exception:
            pass
        if os.path.exists(out) and os.path.getsize(out) > 1000:
            shots[s["key"]] = "screenshots/" + s["key"] + ".png"
            print("  [ OK ]  Picture of %s" % s["name"])
        else:
            warn("No picture of %s (that's OK, the game shows a drawing instead)" % s["name"])
    return shots


# ---------------------------------------------------------------- main
def main():
    no_shots = "--no-screenshots" in sys.argv
    now = datetime.datetime.now()
    stamp = now.strftime("%Y-%m-%d_%H%M")
    dest = os.path.join(TWIN, stamp)
    os.makedirs(dest, exist_ok=True)

    services = []
    for key, name, port, host in SERVICES:
        code = http_code(port)
        services.append({"key": key, "name": name, "port": port, "host": host, "code": code,
                         "up": 0 < code < 500})
    print("  [ OK ]  Checked %d servers (%d up)" % (len(services), sum(s["up"] for s in services)))

    os_name = ""
    try:
        for line in open("/etc/os-release"):
            if line.startswith("PRETTY_NAME="):
                os_name = line.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    ip = run("ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i==\"src\"){print $(i+1); exit}}'")
    ram = 0.0
    try:
        ram = round(int(open("/proc/meminfo").read().split("MemTotal:")[1].split()[0]) / 1048576, 1)
    except Exception:
        pass

    outputs = {
        "hostname": run("hostname"),
        "whoami": USER,
        "uname -a": run("uname -a"),
        "uptime": run("uptime"),
        "date": run("date"),
        "os-release": run("cat /etc/os-release"),
        "lsblk": run("lsblk"),
        "lsblk -f": run("lsblk -f -e 7"),
        "df -h": run("df -h -x tmpfs -x devtmpfs -x squashfs -x overlay -x efivarfs"),
        "free -h": run("free -h"),
        "ip -4 -br a": run("ip -4 -br a"),
        "ip route get 1.1.1.1": run("ip route get 1.1.1.1"),
        "groups": run("groups"),
        "docker ps": run("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"),
        "status.sh": run("bash '%s/status.sh'" % REPO, timeout=60),
        "git log": run("git -C '%s' log --oneline -15" % REPO),
        "ss -ltn": run("ss -ltn"),
        "ps": run("ps -eo pid,comm,args --no-headers | grep -E 'kiwix|jellyfin|caciquedash|dockerd' | grep -v grep"),
        "flatpak list": run("flatpak list --app --columns=application 2>/dev/null"),
        "ufw": run("sudo -n ufw status 2>/dev/null || echo '(needs your password - not captured)'"),
    }
    print("  [ OK ]  Saved what %d commands printed" % len(outputs))

    trees = {"repo": tree(REPO, 4, private_rel=PRIVATE_REPO), "home": home_tree()}
    trees["repo"]["n"] = "elcaciquedeck"
    if os.path.isdir(LIBRARY) and os.listdir(LIBRARY):
        trees["library"] = tree(LIBRARY, 5, max_entries=200)
        trees["library"]["n"] = "Library"
        print("  [ OK ]  Library drive: folders and names")
    else:
        warn("Library drive not connected - the twin will show it unplugged")
    v = vault_tree()
    if v:
        trees["vault"] = v
        print("  [ OK ]  Vault drive: only folder sizes (private)")
    else:
        warn("Vault drive not connected - the twin will show it unplugged")

    snap = {
        "version": 1,
        "demo": False,
        "taken": now.isoformat(timespec="seconds"),
        "stamp": stamp,
        "meta": {
            "host": socket.gethostname(), "user": USER, "os": os_name,
            "kernel": run("uname -r"), "ip": ip, "ram_gb": ram,
            "commit": run("git -C '%s' log -1 --format='%%h %%s'" % REPO),
        },
        "services": services,
        "drives": drives(),
        "outputs": outputs,
        "env": env_files(),
        "trees": trees,
        "screenshots": {} if no_shots else screenshots(os.path.join(dest, "screenshots"), services),
        "warnings": warnings,
    }
    with open(os.path.join(dest, "snapshot.json"), "w") as f:
        json.dump(snap, f, ensure_ascii=False, separators=(",", ":"))

    # newest -> "latest" (relative link so it also works inside the Caddy container)
    link = os.path.join(TWIN, "latest")
    if os.path.islink(link) or os.path.exists(link):
        os.remove(link)
    os.symlink(stamp, link)

    # keep the newest KEEP snapshots, write the list for the time machine
    stamps = sorted(d for d in os.listdir(TWIN) if re.match(r"\d{4}-\d{2}-\d{2}_\d{4}$", d))
    for old in stamps[:-KEEP]:
        shutil.rmtree(os.path.join(TWIN, old), ignore_errors=True)
    stamps = stamps[-KEEP:]
    with open(os.path.join(TWIN, "index.json"), "w") as f:
        json.dump({"latest": stamp, "snapshots": stamps}, f)

    print("  [ OK ]  Snapshot saved: %s" % dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
