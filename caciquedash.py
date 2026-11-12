#!/usr/bin/env python3
"""
ElCaciqueDeck Dashboard - CaciqueGauges: the Home Lab health page ("Aero Naturaleza" panels, no dials).

Start:  python3 caciquedash.py          (opens on port 8888)
Stop:   Ctrl+C
View:   http://localhost:8888  or  http://<laptop number>:8888
Log:    one reading per minute is saved to ~/deck-logs/deck-log-YYYY-MM-DD.csv
        (one file per day, opens in any spreadsheet app)

No internet needed. Uses only what Ubuntu already has (Python 3).
"""
import csv, json, os, socket, sys, threading, time, glob
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8888
SERVICES = {
    "LIBRARY": 8080,   # CaciqueLibrary (Kiwix)
    "FLIX": 8096,      # CaciqueFlix (Jellyfin)
    "DOCS": 8000,      # CaciqueDocs (Paperless)
    "GUARD": 3000,     # CaciqueGuard (AdGuard Home)
    "NAMES": 80,       # Cacique names (Caddy)
    "PHOTOS": 2283,    # CaciquePhotos (Immich)
    "HOME": 8123,      # CaciqueHome (Home Assistant)
    "FRONT": 3001,     # Cacique front page (Homepage)
    "ARCADE": 8090,    # CaciqueArcade (RomM)
    "ACADEMY": 8095,   # CaciqueAcademy (game)
    "VAULT": 8222,     # CaciqueVault (password safe, inside the laptop)
}
LOG_DIR = os.path.expanduser("~/deck-logs")
LOG_EVERY = 60  # seconds between log lines

state = {}
lock = threading.Lock()


def read(path, default=None):
    try:
        with open(path) as f:
            return f.read().strip()
    except Exception:
        return default


def cpu_times():
    parts = read("/proc/stat", "cpu 0 0 0 0").splitlines()[0].split()[1:]
    vals = [int(x) for x in parts]
    idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
    return idle, sum(vals)


def net_bytes():
    rx = tx = 0
    for line in (read("/proc/net/dev", "") or "").splitlines()[2:]:
        name, data = line.split(":", 1)
        name = name.strip()
        if name == "lo" or name.startswith(("docker", "veth", "virbr", "br-")):
            continue
        d = data.split()
        rx += int(d[0]); tx += int(d[8])
    return rx, tx


def cpu_temp():
    best = None
    for hw in glob.glob("/sys/class/hwmon/hwmon*"):
        name = read(hw + "/name", "")
        if name in ("coretemp", "k10temp", "zenpower", "cpu_thermal", "acpitz", "thinkpad"):
            for t in glob.glob(hw + "/temp*_input"):
                v = read(t)
                if v and v.lstrip("-").isdigit():
                    c = int(v) / 1000
                    if 0 < c < 125:
                        best = max(best or 0, c)
            if best and name in ("coretemp", "k10temp", "zenpower"):
                return round(best, 1)
    if best is None:
        for z in glob.glob("/sys/class/thermal/thermal_zone*/temp"):
            v = read(z)
            if v and v.isdigit():
                best = max(best or 0, int(v) / 1000)
    return round(best, 1) if best else None


def fan_rpm():
    for f in glob.glob("/sys/class/hwmon/hwmon*/fan*_input"):
        v = read(f)
        if v and v.isdigit():
            return int(v)
    v = read("/proc/acpi/ibm/fan")
    if v:
        for line in v.splitlines():
            if line.startswith("speed:"):
                return int(line.split()[1])
    return None


def battery():
    out = {"pct": None, "status": None, "ac": None, "watts": None}
    for b in glob.glob("/sys/class/power_supply/*"):
        typ = read(b + "/type", "")
        if typ == "Battery" and out["pct"] is None:
            cap = read(b + "/capacity")
            out["pct"] = int(cap) if cap and cap.isdigit() else None
            out["status"] = read(b + "/status")
            p = read(b + "/power_now")
            if p and p.isdigit():
                out["watts"] = round(int(p) / 1e6, 1)
            else:
                c, v = read(b + "/current_now"), read(b + "/voltage_now")
                if c and v and c.isdigit() and v.isdigit():
                    out["watts"] = round(int(c) * int(v) / 1e12, 1)
        elif typ == "Mains":
            out["ac"] = read(b + "/online") == "1"
    return out


def lan():
    link = False
    iface = None
    for n in sorted(os.listdir("/sys/class/net")):
        if n.startswith(("en", "eth", "wl")) and read("/sys/class/net/%s/operstate" % n) == "up":
            link, iface = True, n
            if n.startswith(("en", "eth")):
                break
    ip = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("1.1.1.1", 53))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass
    return link, iface, ip


def port_open(port, host="127.0.0.1"):
    """A server counts as UP only if it answers a web request without a server error.
    (An open port that answers 500 is 'on but broken' - shown as down, like the Homepage does.)"""
    import http.client
    try:
        conn = http.client.HTTPConnection(host, port, timeout=1.5)
        conn.request("GET", "/", headers={"User-Agent": "CaciqueDash"})
        status = conn.getresponse().status
        conn.close()
        return status < 500
    except Exception:
        return False


def internet():
    try:
        with socket.create_connection(("1.1.1.1", 53), timeout=1.5):
            return True
    except Exception:
        return False


def disks():
    out = []
    seen = set()
    mounts = (read("/proc/mounts", "") or "").splitlines()
    for line in mounts:
        p = line.split()
        if len(p) < 3:
            continue
        dev, mnt, fs = p[0], p[1].replace("\\040", " "), p[2]
        if not dev.startswith("/dev/") or fs in ("squashfs", "vfat") or dev in seen:
            continue
        if mnt == "/" or mnt.startswith(("/media/", "/mnt/")):
            seen.add(dev)
            try:
                st = os.statvfs(mnt)
                total = st.f_blocks * st.f_frsize
                free = st.f_bavail * st.f_frsize
                if total > 0:
                    out.append({
                        "name": "SYSTEM" if mnt == "/" else os.path.basename(mnt).upper()[:10],
                        "pct": round((total - free) / total * 100),
                        "free_gb": round(free / 1e9),
                        "total_gb": round(total / 1e9),
                    })
            except Exception:
                pass
    return out


LOG_FIELDS = ["time", "cpu_pct", "temp_c", "ram_pct", "ram_used_gb", "battery_pct",
              "battery_status", "ac_power", "watts", "fan_rpm", "net_down_mbps",
              "net_up_mbps", "lan", "internet", "disk1_pct", "disk2_pct"] + \
             [k.lower() + "_up" for k in SERVICES]


def write_log(s):
    """Append one reading to today's CSV file. Never crashes the dashboard."""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        path = os.path.join(LOG_DIR, "deck-log-%s.csv" % time.strftime("%Y-%m-%d"))
        base, n = path, 1
        while os.path.exists(path):
            with open(path) as f:
                header = f.readline().strip()
            if header == ",".join(LOG_FIELDS):
                break
            # columns changed after an update: use a fresh file for the rest of the day
            n += 1
            path = base.replace(".csv", "-v%d.csv" % n)
        new = not os.path.exists(path)
        d = s.get("disks") or []
        b = s.get("bat") or {}
        row = [time.strftime("%Y-%m-%d %H:%M:%S"), s["cpu"], s["temp"], s["ram_pct"],
               s["ram_used_gb"], b.get("pct"), b.get("status"), b.get("ac"), b.get("watts"),
               s["fan"], s["rx"], s["tx"], s["link"], s["internet"],
               d[0]["pct"] if len(d) > 0 else None, d[1]["pct"] if len(d) > 1 else None]
        row += [s["services"].get(k) for k in SERVICES]
        with open(path, "a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(LOG_FIELDS)
            w.writerow(["" if v is None else v for v in row])
    except Exception as e:
        print("Log write failed:", e)


def sampler():
    idle0, total0 = cpu_times()
    rx0, tx0 = net_bytes()
    t0 = time.time()
    net_ok, net_checked = None, 0
    last_log = 0
    svc, svc_checked = {}, 0
    while True:
        time.sleep(1)
        idle1, total1 = cpu_times()
        rx1, tx1 = net_bytes()
        t1 = time.time()
        dt = max(t1 - t0, 0.001)
        dtotal = max(total1 - total0, 1)
        cpu = round(100 * (1 - (idle1 - idle0) / dtotal), 1)
        rx_mbps = (rx1 - rx0) * 8 / dt / 1e6
        tx_mbps = (tx1 - tx0) * 8 / dt / 1e6
        idle0, total0, rx0, tx0, t0 = idle1, total1, rx1, tx1, t1

        mem = {}
        for line in (read("/proc/meminfo", "") or "").splitlines():
            k, v = line.split(":", 1)
            mem[k] = int(v.split()[0])
        mt = mem.get("MemTotal", 1)
        ma = mem.get("MemAvailable", mt)

        if t1 - net_checked > 15:
            net_ok, net_checked = internet(), t1
        if t1 - svc_checked > 5:      # web checks every 5 seconds is plenty
            svc, svc_checked = {k: port_open(p) for k, p in SERVICES.items()}, t1
        link, iface, ip = lan()
        up = float((read("/proc/uptime", "0") or "0").split()[0])
        load = (read("/proc/loadavg", "0 0 0") or "0 0 0").split()[:3]

        snap = {
            "host": socket.gethostname(),
            "cpu": cpu,
            "cores": os.cpu_count(),
            "load": load,
            "ram_pct": round((mt - ma) / mt * 100, 1),
            "ram_used_gb": round((mt - ma) / 1048576, 1),
            "ram_total_gb": round(mt / 1048576, 1),
            "temp": cpu_temp(),
            "fan": fan_rpm(),
            "bat": battery(),
            "rx": round(rx_mbps, 2),
            "tx": round(tx_mbps, 2),
            "link": link, "iface": iface, "ip": ip,
            "internet": net_ok,
            "uptime": int(up),
            "disks": disks(),
            "services": svc,
            "time": time.strftime("%H:%M:%S"),
        }
        with lock:
            state.clear(); state.update(snap)
        if t1 - last_log >= LOG_EVERY:
            last_log = t1
            write_log(snap)


PAGE = r"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>CaciqueGauges</title>
<style>
/* CaciqueGauges - "Aero Naturaleza" health page. Same readings as before; no dials.
   Light by day; "Noche" switch for a screen left on overnight. Offline: no fonts or images from outside. */
:root{
 --ink:#102E39;--ink2:#3E5D66;--aqua:#36B7BB;--aqua-deep:#157989;--sun:#F2B862;
 --ok:#22865D;--warn:#A46A24;--bad:#C05050;--off:#7d8f93;
 --panel1:rgba(255,255,255,.86);--panel2:rgba(243,255,248,.66);--card:rgba(255,255,255,.93);--line:rgba(255,255,255,.95);
 --edge:#d5ebe6;--track:linear-gradient(180deg,#dfe9e7,#f4f8f7);
 --sky:radial-gradient(circle at 82% 6%,rgba(255,240,180,.95) 0,rgba(255,238,171,.4) 9%,transparent 26%),radial-gradient(ellipse 120% 80% at 50% 0%,#fdfdf2 0%,#dff6f3 38%,#bfe6da 70%,#9fd3c2 100%);
 --hills:.55;--shadow:0 14px 38px rgba(24,102,98,.14),inset 0 1px 0 #fff;
 --gloss:linear-gradient(180deg,rgba(255,255,255,.75) 0%,rgba(255,255,255,.2) 49%,rgba(255,255,255,0) 50%);
 --font:"Segoe UI","Frutiger","Univers","Ubuntu",-apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif;
 color-scheme:light}
body.night{
 --ink:#e8f6f5;--ink2:#a9c6c9;--aqua-deep:#6fd6d6;--ok:#57d39a;--warn:#f2b862;--bad:#ff8a80;--off:#7f9599;
 --panel1:rgba(20,48,60,.78);--panel2:rgba(14,36,46,.66);--card:rgba(24,56,68,.9);--line:rgba(255,255,255,.14);
 --edge:rgba(255,255,255,.1);--track:linear-gradient(180deg,#0e2630,#1a3a46);
 --sky:radial-gradient(circle at 82% 6%,rgba(190,220,255,.35) 0,rgba(160,200,255,.1) 8%,transparent 22%),radial-gradient(ellipse 120% 80% at 50% 0%,#24435a 0%,#163244 45%,#0d2230 80%,#0a1b26 100%);
 --hills:.35;--shadow:0 14px 38px rgba(0,0,0,.35),inset 0 1px 0 rgba(255,255,255,.08);
 --gloss:linear-gradient(180deg,rgba(255,255,255,.35) 0%,rgba(255,255,255,.08) 49%,rgba(255,255,255,0) 50%);
 color-scheme:dark}
*{box-sizing:border-box}
html,body{margin:0;min-height:100%}
body{font-family:var(--font);color:var(--ink);background:var(--sky) fixed,#bfe6da;overflow-x:hidden;transition:background .4s}
body.night{background:var(--sky) fixed,#0d2230}
body::before{content:"";position:fixed;left:0;right:0;bottom:0;height:40vh;z-index:0;pointer-events:none;opacity:var(--hills);
 background:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1600 420' preserveAspectRatio='none'><path d='M0 265C135 197 242 232 374 183C517 128 622 224 732 182C843 139 912 123 1007 168C1149 234 1208 85 1373 138C1475 169 1507 132 1600 120V420H0Z' fill='%238abeaf'/><path d='M0 323C149 237 202 299 350 253C492 210 600 286 722 238C811 204 917 249 996 235C1108 214 1229 236 1304 178C1450 103 1538 215 1600 193V420H0Z' fill='%2375b3a4'/><path d='M0 365C173 300 280 363 426 306C565 257 723 378 865 286C998 207 1073 332 1239 282C1399 246 1493 298 1600 266V420H0Z' fill='%234f9d8b'/></svg>") center bottom/100% 100% no-repeat}
.wrap{position:relative;z-index:1;max-width:1180px;margin:0 auto;
 padding:max(18px,env(safe-area-inset-top)) max(16px,env(safe-area-inset-right)) max(28px,env(safe-area-inset-bottom)) max(16px,env(safe-area-inset-left));
 display:grid;gap:20px}
:focus-visible{outline:3px solid var(--sun);outline-offset:3px}
.en{color:var(--ink2);font-weight:500}
/* header */
header{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:12px}
.orb{width:52px;height:52px;border-radius:50%;display:grid;place-items:center;flex:0 0 auto;
 background:var(--gloss),radial-gradient(circle at 50% 120%,#8ff0dd 0%,#2fb5ad 45%,#146b79 100%);
 border:1px solid rgba(255,255,255,.9);box-shadow:0 8px 20px rgba(23,102,115,.3),inset 0 -3px 8px rgba(0,60,70,.25)}
.orb svg{width:28px;height:28px;color:#fff;filter:drop-shadow(0 1px 1px rgba(0,0,0,.3))}
.name{font-size:23px;font-weight:750;letter-spacing:-.4px;line-height:1.1}
.sub{font-size:12px;letter-spacing:1.2px;text-transform:uppercase;color:var(--ink2);margin-top:3px}
.tools{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.chip{font-size:15px;color:var(--ink2);background:var(--panel1);border:1px solid var(--line);border-radius:999px;padding:8px 14px}
.seg{display:flex;gap:4px}.seg .btn{padding:0 12px;opacity:.6}.seg .btn[aria-pressed="true"]{opacity:1;border-color:var(--aqua)}
.btn{appearance:none;cursor:pointer;min-height:44px;padding:0 16px;border-radius:14px;font:650 15px var(--font);color:var(--ink);
 border:1px solid var(--edge);background:var(--gloss),var(--card);box-shadow:0 4px 12px rgba(21,106,128,.12)}
/* panels */
.panel{background:linear-gradient(115deg,var(--panel1),var(--panel2));border:1px solid var(--line);border-radius:28px;box-shadow:var(--shadow);
 -webkit-backdrop-filter:blur(18px) saturate(130%);backdrop-filter:blur(18px) saturate(130%);padding:22px 24px}
h2{margin:0 0 14px;font-size:21px;letter-spacing:-.4px;line-height:1.3}
h2 svg{width:24px;height:24px;color:var(--aqua-deep);vertical-align:-5px;margin-right:8px}
/* the big verdict */
.verdict{display:flex;align-items:center;gap:18px;flex-wrap:wrap}
.vicon{width:64px;height:64px;border-radius:50%;display:grid;place-items:center;flex:0 0 auto;color:#fff;
 background:var(--gloss),radial-gradient(circle at 50% 120%,#7ee0a6,#22865D 70%);box-shadow:0 8px 18px rgba(34,134,93,.35)}
.vicon svg{width:34px;height:34px}
.verdict[data-v="warn"] .vicon{background:var(--gloss),radial-gradient(circle at 50% 120%,#ffd58a,#c5821f 70%);box-shadow:0 8px 18px rgba(196,130,31,.35)}
.verdict[data-v="bad"] .vicon{background:var(--gloss),radial-gradient(circle at 50% 120%,#ffb0a8,#C05050 70%);box-shadow:0 8px 18px rgba(192,80,80,.35)}
.verdict[data-v="wait"] .vicon{background:var(--gloss),radial-gradient(circle at 50% 120%,#c9e3e6,#7d8f93 70%)}
.vtext{flex:1 1 280px;min-width:0}
.vtitle{font-size:clamp(24px,3.2vw,34px);font-weight:750;letter-spacing:-.8px;line-height:1.15}
.vsub{font-size:16px;color:var(--ink2);margin-top:4px;line-height:1.45}
.facts{display:flex;flex-wrap:wrap;gap:8px 18px;margin-top:10px;font-size:15px;color:var(--ink2)}
.facts b{color:var(--ink);font-weight:650}
/* metric cards */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--edge);border-radius:22px;padding:16px 18px;box-shadow:0 6px 16px rgba(44,138,117,.12),inset 0 1px 0 rgba(255,255,255,.6);min-width:0}
.ctop{display:flex;align-items:center;justify-content:space-between;gap:8px}
.clabel{font-size:16px;font-weight:700;line-height:1.25}
.clabel .en{display:block;font-size:13px;font-weight:500}
.ctop{align-items:flex-start!important}
.state{font-size:13px;font-weight:700;display:inline-flex;align-items:center;gap:5px;white-space:nowrap}
.state svg{width:16px;height:16px;stroke-width:2.4}
.big{font-size:38px;font-weight:750;letter-spacing:-1px;margin:6px 0 2px;font-variant-numeric:tabular-nums;line-height:1.1}
.big small{font-size:18px;font-weight:650;color:var(--ink2);letter-spacing:0;margin-left:2px}
.detail{font-size:14px;color:var(--ink2);min-height:20px}
/* Vista-style glossy bar */
.bar{position:relative;height:16px;border-radius:9px;margin:10px 0 4px;background:var(--track);border:1px solid var(--edge);overflow:hidden;
 box-shadow:inset 0 1px 3px rgba(0,0,0,.12)}
.fill{position:absolute;left:0;top:0;bottom:0;width:0;border-radius:8px;transition:width .8s cubic-bezier(.2,.7,.2,1);
 background:var(--gloss),linear-gradient(180deg,#5fd88f,#22865D)}
[data-s="warn"] .fill{background:var(--gloss),linear-gradient(180deg,#ffd27a,#c5821f)}
[data-s="bad"] .fill{background:var(--gloss),linear-gradient(180deg,#ff9b90,#C05050)}
[data-s="ok"] .state{color:var(--ok)} [data-s="warn"] .state{color:var(--warn)} [data-s="bad"] .state{color:var(--bad)} [data-s="na"] .state{color:var(--off)}
.spark{width:100%;height:46px;display:block;margin-top:6px}
.spark .area{fill:rgba(54,183,187,.16)} .spark .line{fill:none;stroke:var(--aqua);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
[data-s="warn"] .spark .line{stroke:#c5821f} [data-s="bad"] .spark .line{stroke:var(--bad)}
.sparkcap{font-size:12px;color:var(--ink2);display:flex;justify-content:space-between}
/* drives, like the Vista "Computer" window */
.drives{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}
.drive{display:flex;gap:14px;align-items:center}
.dicon{width:56px;height:56px;flex:0 0 56px;border-radius:16px;display:grid;place-items:center;
 background:var(--gloss),linear-gradient(180deg,#f4fffc,#d3efe8);border:1px solid #fff;box-shadow:0 4px 10px rgba(21,106,128,.14)}
body.night .dicon{background:var(--gloss),linear-gradient(180deg,#2a5866,#173a46);border-color:rgba(255,255,255,.12)}
.dicon svg{width:30px;height:30px;color:var(--aqua-deep)}
.dtext{flex:1;min-width:0}
.dname{font-size:17px;font-weight:750}
.dfree{font-size:14px;color:var(--ink2)}
.drive .fill{background:var(--gloss),linear-gradient(180deg,#6fd0f0,#1f8fb8)}
.drive[data-s="warn"] .fill{background:var(--gloss),linear-gradient(180deg,#ffd27a,#c5821f)}
.drive[data-s="bad"] .fill{background:var(--gloss),linear-gradient(180deg,#ff9b90,#C05050)}
/* apps and connection */
.apps{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:10px}
.app{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:16px;background:var(--card);border:1px solid var(--edge);min-width:0}
.app b{font-size:15px;display:block}
.app span{font-size:13px;font-weight:700}
.dot{width:26px;height:26px;flex:0 0 26px;border-radius:50%;display:grid;place-items:center;color:#fff;background:var(--gloss),radial-gradient(circle at 50% 120%,#7ee0a6,#22865D 70%)}
.dot svg{width:15px;height:15px;stroke-width:2.6}
.app.down .dot{background:var(--gloss),radial-gradient(circle at 50% 120%,#c9d3d5,#7d8f93 70%)}
.app.up span{color:var(--ok)} .app.down span{color:var(--off)}
.two{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(0,1fr);gap:20px;align-items:start}
.kv{display:grid;grid-template-columns:auto 1fr;gap:8px 16px;font-size:15px;margin:0}
.kv dt{color:var(--ink2)} .kv dd{margin:0;text-align:right;font-weight:650;overflow-wrap:anywhere}
footer{text-align:center;font-size:14px;color:var(--ink2);line-height:1.6}
footer.lost{color:var(--bad);font-weight:700}
@media(max-width:900px){.two{grid-template-columns:minmax(0,1fr)}}
@media(max-width:600px){.panel{padding:16px;border-radius:22px}.big{font-size:32px}.name{font-size:20px}.grid,.drives{grid-template-columns:minmax(0,1fr)}
 .apps{grid-template-columns:minmax(0,1fr)}.chip{font-size:14px}}
@media(prefers-reduced-motion:reduce){*{transition:none!important}}
</style></head>
<body>
<div class="wrap">
 <header>
  <div class="brand"><span class="orb" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12h4l2.5-6 4 12 2.5-6H21"/></svg></span>
   <div><div class="name">CaciqueGauges</div><div class="sub"><span data-es="Salud del Home Lab" data-en="Home Lab health">Salud del Home Lab</span></div></div></div>
  <div class="tools"><span class="chip" id="clock">—</span><div class="seg" role="group" aria-label="Idioma · Language"><button class="btn" type="button" data-lang="es">ES</button><button class="btn" type="button" data-lang="en">EN</button></div><button class="btn" id="unitBtn" type="button">°F</button><button class="btn" id="nightBtn" type="button" aria-pressed="false">🌙 Noche</button></div>
 </header>

 <section class="panel" aria-live="polite">
  <div class="verdict" id="verdict" data-v="wait">
   <div class="vicon" id="vicon" aria-hidden="true"></div>
   <div class="vtext"><div class="vtitle" id="vtitle"><span data-es="Revisando…" data-en="Checking…">Revisando…</span></div>
    <div class="vsub" id="vsub"><span data-es="Leyendo el estado del servidor." data-en="Reading the server's health.">Leyendo el estado del servidor.</span></div>
    <div class="facts" id="facts"></div></div>
  </div>
 </section>

 <section class="panel" aria-labelledby="h-now">
  <h2 id="h-now"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="3"/><path d="M9 9h6v6H9z"/></svg><span data-es="Ahora mismo" data-en="Right now">Ahora mismo</span></h2>
  <div class="grid" id="metrics"></div>
 </section>

 <section class="panel" aria-labelledby="h-drives">
  <h2 id="h-drives"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="7" width="18" height="10" rx="2.5"/><path d="M7 12h.01M11 12h6"/></svg><span data-es="Discos" data-en="Drives">Discos</span></h2>
  <div class="drives" id="drives"></div>
 </section>

 <div class="two">
  <section class="panel" aria-labelledby="h-apps">
   <h2 id="h-apps"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="7" height="7" rx="2"/><rect x="13" y="4" width="7" height="7" rx="2"/><rect x="4" y="13" width="7" height="7" rx="2"/><rect x="13" y="13" width="7" height="7" rx="2"/></svg><span data-es="Aplicaciones" data-en="Apps">Aplicaciones</span></h2>
   <div class="apps" id="apps"></div>
  </section>
  <section class="panel" aria-labelledby="h-net">
   <h2 id="h-net"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2.5 9a14 14 0 0 1 19 0M5.5 12.5a9.5 9.5 0 0 1 13 0M8.8 16a4.8 4.8 0 0 1 6.4 0"/><circle cx="12" cy="19" r="1"/></svg><span data-es="Conexión y equipo" data-en="Connection &amp; computer">Conexión y equipo</span></h2>
   <dl class="kv" id="kv"></dl>
  </section>
 </div>
 <footer id="foot"><span data-es="Conectando…" data-en="Connecting…">Conectando…</span></footer>
</div>
<script>
const $=id=>document.getElementById(id);
// one language at a time (Spanish or English), remembered on this device
let LANG="es";try{LANG=localStorage.getItem("cqLang")||((navigator.language||"es").toLowerCase().startsWith("en")?"en":"es")}catch(e){}
const L=(es,en)=>LANG==="en"?en:es, LOC=()=>LANG==="en"?"en-US":"es-PR";
function applyLang(){document.documentElement.lang=LANG;document.querySelectorAll("[data-es]").forEach(e=>{e.textContent=e.dataset[LANG]});
 document.querySelectorAll(".seg [data-lang]").forEach(b=>b.setAttribute("aria-pressed",b.dataset.lang===LANG));}
const ICON={ok:'<path d="m5 12.5 4.5 4.5L19 7.5"/>',warn:'<path d="M12 7v6M12 17h.01"/>',bad:'<path d="M7 7l10 10M17 7 7 17"/>',na:'<path d="M6 12h12"/>',wait:'<path d="M12 6v6l3.5 2"/><circle cx="12" cy="12" r="8.5"/>',
 drive:'<rect x="3" y="7" width="18" height="10" rx="2.5"/><path d="M7 12h.01M11 12h6"/>'};
const svg=(n,c)=>`<svg ${c?`class="${c}"`:""} viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICON[n]}</svg>`;
const WORD={ok:["Normal","Normal"],warn:["Alto","High"],bad:["Crítico","Critical"],na:["Sin sensor","No sensor"]};
const APPNAMES={LIBRARY:"CaciqueLibrary",FLIX:"CaciqueFlix",DOCS:"CaciqueDocs",GUARD:"CaciqueGuard",NAMES:["Nombres","Names"],PHOTOS:"CaciquePhotos",
 HOME:"CaciqueHome",FRONT:["Cacique (portada)","Cacique (front page)"],ARCADE:"CaciqueArcade",ACADEMY:"CaciqueAcademy",VAULT:"CaciqueVault"};
const appName=k=>{const a=APPNAMES[k];return Array.isArray(a)?L(...a):(a||k)};
const HIST={cpu:[],temp:[],ram:[],net:[]}, KEEP=300;   // last 5 minutes, one reading per second
const lvl=(v,w,b)=>v==null||isNaN(v)?"na":v>=b?"bad":v>=w?"warn":"ok";

function spark(arr,max){
 if(arr.length<2)return'<svg class="spark" viewBox="0 0 300 46" preserveAspectRatio="none" aria-hidden="true"></svg>';
 const m=Math.max(max||0,...arr,1),n=arr.length,x=i=>300*i/(n-1),y=v=>44-40*(v/m);
 const pts=arr.map((v,i)=>x(i).toFixed(1)+","+y(v).toFixed(1)).join(" ");
 return`<svg class="spark" viewBox="0 0 300 46" preserveAspectRatio="none" aria-hidden="true"><polygon class="area" points="${x(0)},46 ${pts} ${x(n-1)},46"/><polyline class="line" points="${pts}"/></svg>`;
}
function card(id,label,en,value,unit,pct,s,detail,hist,max){
 const st=L(...WORD[s]), name=L(label,en);
 return`<article class="card" data-s="${s}" aria-label="${name} ${value==null?"":value+unit}, ${st}">
  <div class="ctop"><span class="clabel">${name}</span><span class="state">${svg(s)}${st}</span></div>
  <div class="big">${value==null?"—":value}<small>${value==null?"":unit}</small></div>
  ${pct==null?"":`<div class="bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(pct)}"><div class="fill" style="width:${Math.max(0,Math.min(100,pct))}%"></div></div>`}
  <div class="detail">${detail||""}</div>
  ${hist?spark(hist,max)+`<div class="sparkcap"><span>${since(hist.length)}</span><span>${L("ahora","now")}</span></div>`:""}
 </article>`;
}
function since(n){const t=n>=KEEP?"5 min":n<60?n+" s":Math.floor(n/60)+" min";return L("hace "+t,t+" ago")}
function upFmt(s){const d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60);
 return(d?d+" d ":"")+h+" h "+m+" min";}
function push(k,v){if(v==null||isNaN(v))return;HIST[k].push(v);if(HIST[k].length>KEEP)HIST[k].shift();}

let lost=0;
async function tick(){
 try{
  const r=await fetch("/api",{cache:"no-store"});const s=await r.json();
  if(!s.host)return;
  lost=0;
  const net=+(s.rx+s.tx).toFixed(1);
  push("cpu",s.cpu);push("temp",s.temp);push("ram",s.ram_pct);push("net",net);
  const b=s.bat||{}, d=s.disks||[];
  const cS=lvl(s.cpu,70,90), tS=lvl(s.temp,70,85), rS=lvl(s.ram_pct,80,92);
  const bS=b.pct==null?"na":(b.pct<15&&!b.ac?"bad":b.pct<30&&!b.ac?"warn":"ok");
  let M="";
  M+=card("cpu","Procesador","CPU",Math.round(s.cpu),"%",s.cpu,cS,L(`Carga ${s.load[0]} · ${s.cores} núcleos`,`Load ${s.load[0]} · ${s.cores} cores`),HIST.cpu,100);
  M+=card("temp","Temperatura","Temperature",s.temp==null?null:Math.round(FAHR?s.temp*9/5+32:s.temp),FAHR?"°F":"°C",s.temp==null?null:Math.min(100,(s.temp-30)/(95-30)*100),tS,
   s.temp==null?L("Este equipo no muestra la temperatura","No temperature sensor"):(s.temp<70?L("Cómodo","Comfortable"):s.temp<85?L("Caliente: revisa la ventilación","Warm: check the airflow"):L("Muy caliente","Very hot")),HIST.temp,95);
  M+=card("ram","Memoria","Memory",Math.round(s.ram_pct),"%",s.ram_pct,rS,L(`${s.ram_used_gb} de ${s.ram_total_gb} GB en uso`,`${s.ram_used_gb} of ${s.ram_total_gb} GB in use`),HIST.ram,100);
  M+=card("net","Red","Network",net,"Mbps",null,s.link?"ok":"bad",`↓ ${s.rx.toFixed(1)} · ↑ ${s.tx.toFixed(1)} Mbps`,HIST.net,null);
  M+=card("bat",b.ac===false?"Batería":"Corriente",b.ac===false?"Battery":"Power",b.pct,"%",b.pct,bS,
   b.pct==null?L("Sin batería","No battery"):(({Charging:["Cargando","Charging"],Discharging:["Usando la batería","On battery"],Full:["Llena","Full"],"Not charging":["Conectada","Plugged in"]}[b.status]||[b.status||"",b.status||""])[LANG==="en"?1:0])+(b.watts?` · ${b.watts} W`:""),null);
  if(s.fan!=null)M+=card("fan","Ventilador","Fan",s.fan,"RPM",Math.min(100,s.fan/60),lvl(s.fan,4500,5500),"",null);
  $("metrics").innerHTML=M;

  $("drives").innerHTML=d.length?d.map(x=>{const ds=lvl(x.pct,85,95);const nm=x.name==="SYSTEM"?L("Sistema","System"):x.name.charAt(0)+x.name.slice(1).toLowerCase();
   return`<div class="drive" data-s="${ds}"><span class="dicon">${svg("drive")}</span><div class="dtext"><div class="dname">${nm}</div>
    <div class="bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${x.pct}" aria-label="${nm} ${x.pct}%"><div class="fill" style="width:${x.pct}%"></div></div>
    <div class="dfree">${L(`${x.free_gb.toLocaleString("es")} GB libres de ${x.total_gb.toLocaleString("es")} GB · ${x.pct}% usado`,`${x.free_gb.toLocaleString("en")} GB free of ${x.total_gb.toLocaleString("en")} GB · ${x.pct}% used`)}</div></div></div>`}).join("")
   :`<p class="dfree">${L("No se ven discos","No drives found")}</p>`;

  const svc=s.services||{};let A="",down=0,tot=0;
  for(const k in svc){tot++;if(!svc[k])down++;
   A+=`<div class="app ${svc[k]?"up":"down"}"><span class="dot">${svg(svc[k]?"ok":"na")}</span><div><b>${appName(k)}</b><span>${svc[k]?L("En línea","Online"):L("Apagada","Off")}</span></div></div>`;}
  $("apps").innerHTML=A;

  $("kv").innerHTML=`<dt>${L("Red de la casa","Home network")}</dt><dd>${s.link?L("Conectada","Connected"):L("Sin conexión","Disconnected")}</dd>
   <dt>Internet</dt><dd>${s.internet==null?L("Revisando…","Checking…"):s.internet?L("Sí","Yes"):L("No (la casa funciona igual)","No (the home still works)")}</dd>
   <dt>${L("Dirección","Address")}</dt><dd>${s.ip||"—"}</dd><dt>${L("Conexión","Interface")}</dt><dd>${s.iface?(s.iface.startsWith("wl")?"Wi-Fi ("+s.iface+")":"Cable ("+s.iface+")"):"—"}</dd>
   <dt>${L("Equipo","Computer")}</dt><dd>${s.host}</dd><dt>${L("Encendido","Up")}</dt><dd>${upFmt(s.uptime)}</dd>`;

  // the one-line verdict
  const worst=[cS,tS,rS,bS,s.link?"ok":"bad",...d.map(x=>lvl(x.pct,85,95))];
  const v=worst.includes("bad")?"bad":worst.includes("warn")?"warn":"ok";
  const T={ok:["Todo funciona bien","Everything is running well"],warn:["Funciona, pero algo necesita atención","Running, but something needs attention"],bad:["Hay un problema","There's a problem"]}[v];
  $("verdict").dataset.v=v;$("vicon").innerHTML=svg(v);
  $("vtitle").textContent=L(...T);
  $("vsub").textContent=v==="ok"?L("Procesador, temperatura, memoria y discos en niveles normales.","CPU, temperature, memory and drives are normal.")
   :L("Mira las tarjetas marcadas en amarillo o rojo.","Look at the cards marked yellow or red.");
  $("facts").innerHTML=`<span>${L("Aplicaciones","Apps")}: <b>${L(`${tot-down} de ${tot} en línea`,`${tot-down} of ${tot} online`)}</b></span><span>${L("Encendido","Up")}: <b>${upFmt(s.uptime)}</b></span><span>Internet: <b>${s.internet?L("Sí","Yes"):s.internet==null?"…":"No"}</b></span>`;
  const f=$("foot");f.className="";f.textContent=L(`En vivo · actualizado ${s.time} · lecturas guardadas cada minuto en ~/deck-logs`,`Live · updated ${s.time} · readings saved every minute in ~/deck-logs`);
 }catch(e){
  if(++lost>=3){const f=$("foot");f.className="lost";f.textContent=L("Sin señal del servidor: revisa la corriente, la red o la computadora.","No signal from the server: check the power, the network or the computer.");
   $("verdict").dataset.v="bad";$("vicon").innerHTML=svg("bad");$("vtitle").textContent=L("Sin señal","No signal");}
 }
}
function clock(){const n=new Date();let t;try{t=n.toLocaleDateString(LOC(),{weekday:"long",day:"numeric",month:"long"})+" · "+n.toLocaleTimeString(LOC(),{hour:"numeric",minute:"2-digit"})}catch(e){t=n.toString()}
 $("clock").textContent=t.charAt(0).toUpperCase()+t.slice(1);}
function night(on,save){document.body.classList.toggle("night",on);$("nightBtn").setAttribute("aria-pressed",on);$("nightBtn").textContent=on?L("☀️ Día","☀️ Day"):L("🌙 Noche","🌙 Night");
 if(save)try{localStorage.setItem("gaugesNight",on?"1":"0")}catch(e){}}
// Puerto Rico reads °F; one tap switches to °C (remembered on this device)
let FAHR=true;try{FAHR=localStorage.getItem("gaugesUnit")!=="C"}catch(e){}
function unitLabel(){$("unitBtn").textContent=FAHR?"°F":"°C";$("unitBtn").title=FAHR?L("Cambiar a °C","Switch to °C"):L("Cambiar a °F","Switch to °F");}
$("unitBtn").onclick=()=>{FAHR=!FAHR;try{localStorage.setItem("gaugesUnit",FAHR?"F":"C")}catch(e){}unitLabel();tick();};
unitLabel();
$("nightBtn").onclick=()=>night(!document.body.classList.contains("night"),true);
let n0=false;try{n0=localStorage.getItem("gaugesNight")==="1"}catch(e){}
document.querySelectorAll(".seg [data-lang]").forEach(b=>b.onclick=()=>{LANG=b.dataset.lang;try{localStorage.setItem("cqLang",LANG)}catch(e){}
 applyLang();unitLabel();night(document.body.classList.contains("night"),false);clock();tick();});
applyLang();night(n0,false);$("vicon").innerHTML=svg("wait");clock();setInterval(clock,30000);tick();setInterval(tick,1000);
</script>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api"):
            with lock:
                body = json.dumps(state).encode()
            ctype = "application/json"
        elif self.path in ("/", "/index.html"):
            body = PAGE.encode()
            ctype = "text/html; charset=utf-8"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    threading.Thread(target=sampler, daemon=True).start()
    time.sleep(1.2)
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("ElCaciqueDeck dashboard running.")
    print("  On this laptop:   http://localhost:%d" % PORT)
    print("  Other devices:    http://<laptop number>:%d" % PORT)
    print("  Logging every minute to: %s" % LOG_DIR)
    print("Press Ctrl+C to stop.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
