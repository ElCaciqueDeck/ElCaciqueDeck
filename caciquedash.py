#!/usr/bin/env python3
"""
ElCaciqueDeck Dashboard - JDM-style system gauges for the home lab.

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
SERVICES = {"KIWIX": 8080, "JELLYFIN": 8096, "PAPERLESS": 8000}
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
    try:
        with socket.create_connection((host, port), timeout=0.4):
            return True
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
            "services": {k: port_open(p) for k, p in SERVICES.items()},
            "time": time.strftime("%H:%M:%S"),
        }
        with lock:
            state.clear(); state.update(snap)
        if t1 - last_log >= LOG_EVERY:
            last_log = t1
            write_log(snap)


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ElCaciqueDeck Gauges</title>
<style>
:root{--glow:#ff8a1c;--glow2:#ffb35c;--red:#ff2a1a;--face:#0b0b0d;--txt:#f4efe6}
body.blue{--glow:#38b6ff;--glow2:#9fdcff}
body.red{--glow:#ff3b2f;--glow2:#ff8a80}
body.white{--glow:#e8f0ff;--glow2:#ffffff}
*{box-sizing:border-box}
html,body{margin:0;min-height:100%;background:#050506;color:var(--txt);
 font-family:"DejaVu Sans Mono","Liberation Mono",Menlo,Consolas,monospace}
body{background:
 repeating-linear-gradient(45deg,#0d0d0f 0 4px,#121215 4px 8px),
 repeating-linear-gradient(-45deg,#0d0d0f 0 4px,#101013 4px 8px);
 background-blend-mode:lighten;padding:16px;overflow-x:hidden}
.top{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;
 max-width:1200px;margin:0 auto 10px}
.brand{font-style:italic;font-weight:900;letter-spacing:.18em;font-size:clamp(16px,3vw,26px);
 color:var(--glow2);text-shadow:0 0 8px var(--glow),0 0 22px var(--glow)}
.brand small{display:block;font-size:.45em;letter-spacing:.5em;color:#8a8478;text-shadow:none;font-style:normal}
button{background:#151518;color:var(--glow2);border:1px solid #333;border-radius:4px;
 font:inherit;font-size:12px;letter-spacing:.2em;padding:8px 12px;cursor:pointer}
button:hover{border-color:var(--glow)}
.cluster{max-width:1200px;margin:0 auto;padding:18px;border-radius:28px;
 background:linear-gradient(#18181b,#0a0a0b);box-shadow:inset 0 2px 0 #2a2a2e,0 20px 50px #000,inset 0 -30px 60px #000}
.main{display:grid;grid-template-columns:1fr 1.25fr 1fr;gap:12px;align-items:center}
.pods{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-top:16px}
.gauge svg{width:100%;height:auto;display:block}
.lcd{background:#0f1410;border:1px solid #222;border-radius:6px;padding:10px 14px;
 color:var(--glow2);text-shadow:0 0 6px var(--glow);font-size:13px;line-height:1.7;letter-spacing:.08em}
.lcd b{color:#fff;font-weight:700}
.lights{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:16px}
.lamp{min-width:92px;text-align:center;padding:7px 10px;border-radius:4px;font-size:11px;font-weight:700;
 letter-spacing:.18em;border:1px solid #2a2a2a;color:#3a3a3a;background:#0c0c0c}
.lamp.on{color:#062a0a;background:#46ff6a;box-shadow:0 0 14px #46ff6a;border-color:#8dff9f}
.lamp.warn{color:#2a1800;background:#ffb000;box-shadow:0 0 14px #ffb000;border-color:#ffd36b}
.lamp.bad{color:#2a0000;background:var(--red);box-shadow:0 0 16px var(--red);border-color:#ff8077}
.sidecol{display:flex;flex-direction:column;gap:12px}
.foot{max-width:1200px;margin:10px auto 0;text-align:center;font-size:11px;color:#5a564e;letter-spacing:.3em}
.needle{transition:transform .9s cubic-bezier(.25,1.4,.5,1)}
@media(max-width:860px){.main{grid-template-columns:1fr 1fr}.main .tach{grid-column:1/-1;order:-1}
 .pods{grid-template-columns:repeat(3,1fr)}}
@media(max-width:520px){.main{grid-template-columns:1fr}.pods{grid-template-columns:repeat(2,1fr)}
 body{padding:10px}.cluster{padding:10px;border-radius:18px}}
</style></head>
<body>
<div class="top">
 <div class="brand">ELCACIQUEDECK<small>HOME LAB INSTRUMENT CLUSTER</small></div>
 <button id="lightBtn" title="Change backlight color">BACKLIGHT: AMBER</button>
</div>
<div class="cluster">
 <div class="main">
  <div class="sidecol">
   <div class="gauge" id="g-temp"></div>
   <div class="lcd" id="lcd-left"></div>
  </div>
  <div class="gauge tach" id="g-cpu"></div>
  <div class="sidecol">
   <div class="gauge" id="g-net"></div>
   <div class="lcd" id="lcd-right"></div>
  </div>
 </div>
 <div class="pods">
  <div class="gauge" id="g-ram"></div>
  <div class="gauge" id="g-bat"></div>
  <div class="gauge" id="g-fan"></div>
  <div class="gauge" id="g-disk0"></div>
  <div class="gauge" id="g-disk1"></div>
 </div>
 <div class="lights" id="lights"></div>
</div>
<div class="foot" id="foot">STARTING ENGINE…</div>

<script>
const NS="http://www.w3.org/2000/svg";
function el(t,a,p){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);if(p)p.appendChild(e);return e}
const START=-225, SWEEP=270;            // classic 270-degree dial, 0 at lower-left
function pt(cx,cy,r,deg){const a=(deg)*Math.PI/180;return[cx+r*Math.cos(a),cy+r*Math.sin(a)]}
function arc(cx,cy,r,a0,a1){const[x0,y0]=pt(cx,cy,r,a0),[x1,y1]=pt(cx,cy,r,a1);
 return`M${x0} ${y0} A${r} ${r} 0 ${a1-a0>180?1:0} 1 ${x1} ${y1}`}

const gauges={};
function makeGauge(id,o){
 const host=document.getElementById(id);host.innerHTML="";
 const big=!!o.big, S=200, c=100;
 const svg=el("svg",{viewBox:`0 0 ${S} ${S}`},host);
 const defs=el("defs",{},svg);
 const bz=el("linearGradient",{id:id+"bz",x1:0,y1:0,x2:0,y2:1},defs);
 el("stop",{offset:"0",  "stop-color":"#e9e9ec"},bz);el("stop",{offset:".45","stop-color":"#6b6b70"},bz);
 el("stop",{offset:".55","stop-color":"#2a2a2e"},bz);el("stop",{offset:"1","stop-color":"#a9a9ae"},bz);
 const fc=el("radialGradient",{id:id+"fc",cx:".5",cy:".42",r:".65"},defs);
 el("stop",{offset:"0","stop-color":"#1d1d22"},fc);el("stop",{offset:"1","stop-color":"#050506"},fc);
 const gl=el("filter",{id:id+"gl",x:"-50%",y:"-50%",width:"200%",height:"200%"},defs);
 el("feGaussianBlur",{stdDeviation:"2.2",result:"b"},gl);
 const m=el("feMerge",{},gl);el("feMergeNode",{in:"b"},m);el("feMergeNode",{in:"SourceGraphic"},m);

 el("circle",{cx:c,cy:c,r:98,fill:`url(#${id}bz)`},svg);
 el("circle",{cx:c,cy:c,r:91,fill:"#000"},svg);
 el("circle",{cx:c,cy:c,r:89,fill:`url(#${id}fc)`},svg);

 const min=o.min||0,max=o.max,rl=o.red;
 const toDeg=v=>START+SWEEP*Math.max(0,Math.min(1,(v-min)/(max-min)));
 if(rl!=null) el("path",{d:arc(c,c,78,toDeg(rl),START+SWEEP),stroke:"var(--red)","stroke-width":big?9:8,fill:"none",opacity:.9,filter:`url(#${id}gl)`},svg);
 if(o.low!=null) el("path",{d:arc(c,c,78,START,toDeg(o.low)),stroke:"var(--red)","stroke-width":big?9:8,fill:"none",opacity:.9,filter:`url(#${id}gl)`},svg);
 el("path",{d:arc(c,c,84,START,START+SWEEP),stroke:"var(--glow)","stroke-width":1.2,fill:"none",opacity:.55},svg);

 const major=o.major, minor=o.minor||major/2;
 for(let v=min;v<=max+1e-9;v+=minor){
  const isMaj=Math.abs(((v-min)/major)-Math.round((v-min)/major))<1e-6;
  const d=toDeg(v), [x0,y0]=pt(c,c,isMaj?70:75,d), [x1,y1]=pt(c,c,84,d);
  const red=(rl!=null&&v>=rl)||(o.low!=null&&v<o.low);
  el("line",{x1:x0,y1:y0,x2:x1,y2:y1,stroke:red?"var(--red)":"var(--txt)","stroke-width":isMaj?2.6:1.2,"stroke-linecap":"round"},svg);
  if(isMaj){const[tx,ty]=pt(c,c,big?57:56,d);
   const t=el("text",{x:tx,y:ty+4,"text-anchor":"middle","font-size":big?13:12,"font-weight":"700","font-style":"italic",
    fill:red?"var(--red)":"var(--glow2)",filter:`url(#${id}gl)`,"font-family":"inherit"},svg);
   t.textContent=o.fmt?o.fmt(v):v;}
 }
 const lab=el("text",{x:c,y:big?124:70,"text-anchor":"middle","font-size":big?11:10,"letter-spacing":"2","fill":"#9b968c","font-family":"inherit"},svg);lab.textContent=o.label;
 if(o.unit){const u=el("text",{x:c,y:big?135:81,"text-anchor":"middle","font-size":8,"letter-spacing":"1.5",fill:"#6c675f","font-family":"inherit"},svg);u.textContent=o.unit;}
 const val=el("text",{x:c,y:big?162:157,"text-anchor":"middle","font-size":big?24:20,"font-weight":"700",fill:"var(--glow2)",filter:`url(#${id}gl)`,"font-family":"inherit"},svg);val.textContent="--";
 const sub=el("text",{x:c,y:big?177:172,"text-anchor":"middle","font-size":8.5,"letter-spacing":"1.5",fill:"#7d786f","font-family":"inherit"},svg);

 const g=el("g",{class:"needle",style:`transform-origin:${c}px ${c}px;transform:rotate(${START}deg)`},svg);
 el("path",{d:`M${c-3} ${c} L${c+(big?80:74)} ${c-1} L${c+(big?80:74)} ${c+1} L${c-3} ${c+2.5} Z`,transform:`translate(0,-0.75)`,fill:"var(--red)",filter:`url(#${id}gl)`},g);
 el("rect",{x:c-22,y:c-2,width:20,height:4,rx:2,fill:"#222"},g);
 el("circle",{cx:c,cy:c,r:big?11:9,fill:"#1a1a1d",stroke:"#555","stroke-width":1.5},svg);
 el("circle",{cx:c,cy:c,r:3,fill:"#666"},svg);
 const warn=el("circle",{cx:c+(big?52:48),cy:c+(big?52:48),r:4,fill:"#300"},svg);
 gauges[id]={toDeg,g,val,sub,warn,o};
}
function setGauge(id,v,text,subtext){
 const G=gauges[id];if(!G)return;
 const ok=v!=null&&!isNaN(v);
 G.g.style.transform=`rotate(${ok?G.toDeg(v):START}deg)`;
 G.val.textContent=ok?(text!=null?text:Math.round(v)):"N/A";
 G.sub.textContent=subtext||"";
 const hot=ok&&((G.o.red!=null&&v>=G.o.red)||(G.o.low!=null&&v<G.o.low));
 G.warn.setAttribute("fill",hot?"var(--red)":"#300");
 G.warn.setAttribute("filter",hot?`url(#${id}gl)`:"");
}

makeGauge("g-cpu",{big:1,label:"CPU LOAD",unit:"x10 %",max:100,major:10,minor:5,red:85,fmt:v=>v/10});
makeGauge("g-temp",{label:"CPU TEMP",unit:"°C",min:30,max:110,major:20,minor:10,red:85});
makeGauge("g-net",{label:"NETWORK",unit:"Mbps",max:100,major:20,minor:10});
makeGauge("g-ram",{label:"RAM",unit:"%",max:100,major:25,red:90});
makeGauge("g-bat",{label:"BATTERY",unit:"%",max:100,major:25,low:15});
makeGauge("g-fan",{label:"FAN",unit:"x1000 RPM",max:6000,major:1000,minor:500,red:5000,fmt:v=>v/1000});
makeGauge("g-disk0",{label:"DISK",unit:"% FULL",max:100,major:25,red:90});
makeGauge("g-disk1",{label:"DISK 2",unit:"% FULL",max:100,major:25,red:90});

function fmtUp(s){const d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60);return`${d}D ${String(h).padStart(2,"0")}H ${String(m).padStart(2,"0")}M`}
function lamp(name,cls){return`<div class="lamp ${cls}">${name}</div>`}

async function tick(){
 try{
  const r=await fetch("/api",{cache:"no-store"});const s=await r.json();
  if(!s.host){return}
  setGauge("g-cpu",s.cpu,Math.round(s.cpu)+"%",`LOAD ${s.load[0]}`);
  setGauge("g-temp",s.temp,s.temp!=null?Math.round(s.temp)+"°":null,s.temp!=null?"":"NO SENSOR");
  const net=s.rx+s.tx;
  setGauge("g-net",Math.min(net,100),net<10?net.toFixed(1):Math.round(net),`↓${s.rx.toFixed(1)} ↑${s.tx.toFixed(1)}`);
  setGauge("g-ram",s.ram_pct,Math.round(s.ram_pct)+"%",`${s.ram_used_gb}/${s.ram_total_gb} GB`);
  const b=s.bat;
  setGauge("g-bat",b.pct,b.pct!=null?b.pct+"%":null,b.status?(({Charging:"CHARGING",Discharging:"ON BATTERY",Full:"FULL","Not charging":"PLUGGED IN"})[b.status]||b.status.toUpperCase())+(b.watts?` ${b.watts}W`:""):"NO BATTERY");
  setGauge("g-fan",s.fan,s.fan!=null?s.fan:null,s.fan!=null?"RPM":"NO SENSOR");
  const d=s.disks||[];
  setGauge("g-disk0",d[0]?d[0].pct:null,d[0]?d[0].pct+"%":null,d[0]?`${d[0].name} ${d[0].free_gb}GB FREE`:"");
  setGauge("g-disk1",d[1]?d[1].pct:null,d[1]?d[1].pct+"%":null,d[1]?`${d[1].name} ${d[1].free_gb}GB FREE`:"NOT MOUNTED");
  document.getElementById("lcd-left").innerHTML=
   `HOST <b>${s.host.toUpperCase()}</b><br>IP&nbsp;&nbsp; <b>${s.ip||"--"}</b><br>LINK <b>${s.iface||"--"}</b>`;
  document.getElementById("lcd-right").innerHTML=
   `UPTIME <b>${fmtUp(s.uptime)}</b><br>CORES&nbsp; <b>${s.cores}</b><br>CLOCK&nbsp; <b>${s.time}</b>`;
  let L="";
  L+=lamp("LAN",s.link?"on":"bad");
  L+=lamp("INTERNET",s.internet==null?"":s.internet?"on":"warn");
  L+=lamp("AC POWER",b.ac==null?"":b.ac?"on":"warn");
  L+=lamp("BATT LOW",b.pct!=null&&b.pct<15?"bad":"");
  L+=lamp("OVERHEAT",s.temp!=null&&s.temp>=85?"bad":"");
  for(const k in s.services)L+=lamp(k,s.services[k]?"on":"");
  document.getElementById("lights").innerHTML=L;
  document.getElementById("foot").textContent=`LIVE · UPDATED ${s.time}`;
 }catch(e){
  document.getElementById("foot").textContent="NO SIGNAL FROM SERVER — IS THE DASHBOARD STILL RUNNING?";
 }
}

// startup needle sweep, like turning the key
function sweep(){
 const ids=Object.keys(gauges);
 ids.forEach(id=>{const G=gauges[id];G.g.style.transform=`rotate(${START+SWEEP}deg)`});
 setTimeout(()=>{ids.forEach(id=>{gauges[id].g.style.transform=`rotate(${START}deg)`});
  setTimeout(()=>{tick();setInterval(tick,1000)},900)},1000);
}

const colors=["","blue","red","white"],names=["AMBER","BLUE","RED","WHITE"];
let ci=0;try{ci=+localStorage.getItem("dashColor")||0}catch(e){}
function applyColor(){document.body.className=colors[ci];document.getElementById("lightBtn").textContent="BACKLIGHT: "+names[ci];
 try{localStorage.setItem("dashColor",ci)}catch(e){}}
document.getElementById("lightBtn").onclick=()=>{ci=(ci+1)%colors.length;applyColor()};
applyColor();sweep();
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
