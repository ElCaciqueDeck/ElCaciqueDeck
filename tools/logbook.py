#!/usr/bin/env python3
"""
ElCaciqueDeck - the Logbook (bitácora): one place where everything that happens to the Home Lab is written,
so people AND CaciqueGuía (the local AI helper) can read the system's history.

  python3 ~/elcaciquedeck/tools/logbook.py add <source> <level> <message>   # level: info, ok, warn, error
  python3 ~/elcaciquedeck/tools/logbook.py collect     # gathers warnings/errors from reports, status, gauges
  python3 ~/elcaciquedeck/tools/logbook.py brief       # a short plain-text summary (what the AI reads)
  python3 ~/elcaciquedeck/tools/logbook.py tail 30     # the last 30 entries

Stored on this laptop only: ~/elcaciquedeck-data/logbook/YYYY-MM.jsonl (one JSON line per event).
start-all.sh, update.sh and the installer call "collect" / "add" by themselves.
No passwords are ever written here (lines that look like secrets are masked).
"""
import csv, datetime, glob, hashlib, json, os, re, subprocess, sys

HOME = os.path.expanduser("~")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOK = os.environ.get("LOGBOOK_DIR") or os.path.join(HOME, "elcaciquedeck-data", "logbook")
SEEN = os.path.join(BOOK, ".seen")
SECRET = re.compile(r"(?i)\b([\w.-]*(?:password|passwd|secret|token|api[_-]?key)[\w.-]*)(\s*[=:]\s*)(\S+)")


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def mask(text):
    return SECRET.sub(lambda m: m.group(1) + m.group(2) + "••••••", str(text))


def add(source, level, message, when=None):
    os.makedirs(BOOK, exist_ok=True)
    when = when or now()
    entry = {"time": when, "source": source, "level": level, "message": mask(message)[:2000]}
    with open(os.path.join(BOOK, when[:7] + ".jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def entries(limit=None):
    out = []
    for path in sorted(glob.glob(os.path.join(BOOK, "*.jsonl"))):
        for line in open(path, encoding="utf-8", errors="replace"):
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out[-limit:] if limit else out


def seen_set():
    try:
        return set(open(SEEN).read().split())
    except Exception:
        return set()


def collect():
    """Bring warnings/errors from the reports, the current status and the gauges into the logbook (no repeats)."""
    seen = seen_set()
    new = 0
    # 1. setup/update reports: every [WARN] and [FAIL] line
    for path in sorted(glob.glob(os.path.join(REPO, "reports", "*.txt")))[-200:]:
        name = os.path.basename(path)
        m = re.search(r"(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})", name)
        when = "%sT%s:%s:00" % m.groups() if m else now()
        for line in open(path, encoding="utf-8", errors="replace"):
            if "[WARN]" in line or "[FAIL]" in line:
                key = hashlib.sha1((name + line).encode()).hexdigest()[:16]
                if key in seen:
                    continue
                seen.add(key)
                add(name.rsplit("-", 2)[0], "error" if "[FAIL]" in line else "warn", line.strip(), when)
                new += 1
    # 2. servers that are down or failing right now
    try:
        out = subprocess.run(["bash", os.path.join(REPO, "status.sh")], capture_output=True, text=True, timeout=90).stdout
        for line in out.splitlines():
            if re.search(r"\s(ERROR|--)\s", line) and "drive" not in line.lower() or "not connected" in line:
                key = hashlib.sha1((now()[:13] + line).encode()).hexdigest()[:16]   # once per hour at most
                if key not in seen:
                    seen.add(key)
                    add("status", "warn", line.strip())
                    new += 1
    except Exception as e:
        add("logbook", "warn", "could not read status: %s" % e)
    # 3. the gauges (CaciqueDash CSV): one summary per day
    for path in sorted(glob.glob(os.path.join(HOME, "deck-logs", "deck-log-*.csv")))[-7:]:
        day = re.search(r"(\d{4}-\d{2}-\d{2})", path)
        key = "dash-" + (day.group(1) if day else path)
        if key in seen or (day and day.group(1) == datetime.date.today().isoformat()):
            continue      # today's file is still growing
        try:
            rows = list(csv.DictReader(open(path, encoding="utf-8")))
            cpu = [float(r.get("cpu_pct") or r.get("cpu") or 0) for r in rows]
            temp = [float(r.get("temp_c") or r.get("temp") or 0) for r in rows]
            ram = [float(r.get("ram_pct") or r.get("ram") or 0) for r in rows]
            if rows:
                add("dash", "info", "Day summary %s: %d readings, CPU avg %.0f%% max %.0f%%, RAM avg %.0f%%, temp max %.0f C"
                    % (day.group(1) if day else "?", len(rows), sum(cpu) / len(cpu), max(cpu),
                       sum(ram) / len(ram) if ram else 0, max(temp) if temp else 0), day.group(1) + "T23:59:00" if day else None)
                new += 1
            seen.add(key)
        except Exception:
            seen.add(key)
    os.makedirs(BOOK, exist_ok=True)
    with open(SEEN, "w") as f:
        f.write("\n".join(sorted(seen)[-20000:]))
    return new


def brief(limit=60):
    """Plain text for people and for the AI: what happened lately."""
    ev = entries()
    lines = ["EL CACIQUE HOME LAB - LOGBOOK (last %d events, newest last)" % min(limit, len(ev))]
    for e in ev[-limit:]:
        lines.append("%s  %-6s %-14s %s" % (e["time"].replace("T", " ")[:16], e["level"].upper(), e["source"][:14], e["message"]))
    if len(ev) <= 0:
        lines.append("(empty - nothing recorded yet)")
    return "\n".join(lines)


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    if a[0] == "add" and len(a) >= 4:
        add(a[1], a[2], " ".join(a[3:]))
    elif a[0] == "collect":
        print("  Logbook: %d new entries" % collect())
    elif a[0] == "brief":
        print(brief())
    elif a[0] == "tail":
        for e in entries(int(a[1]) if len(a) > 1 else 30):
            print("%s  %-6s %-14s %s" % (e["time"], e["level"], e["source"], e["message"]))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
