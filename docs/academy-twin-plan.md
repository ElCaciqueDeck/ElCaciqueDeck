# 🖥️ CaciqueAcademy 2.0 — "El Cacique Admin" (the Digital Twin)

> **Status: DESIGN — buildable on today's hardware** (no new equipment needed).
> *Estado: DISEÑO — se puede construir con el equipo de hoy.*

## The idea / La idea
Not just a Terminal: a **pretend copy of the real ThinkPad desktop** that anyone can log in to and explore.
You sign in as **"El Cacique Admin"** and see a desktop that looks and behaves like the real one —
the Files app, the Terminal, the browser showing the Cacique pages, the Disks app, the dashboard —
**frozen at the last update**. It is not live and not a remote control: it's a **snapshot**, refreshed only
when the real server is updated (`git pull` + `update.sh`).

So you practice on **your own system as it really is**, with zero risk to the real one.

*No es solo una Terminal: es una copia de práctica del escritorio real de la ThinkPad, congelada en la
última actualización. Se practica con el sistema tal como es, sin riesgo para el real.*

## How it works / Cómo funciona

```
 Real ThinkPad                                   The game (in any browser at home)
 ─────────────                                   ─────────────────────────────────
 git pull + update.sh
        │
        ▼
 tools/snapshot.sh  ── takes a "photo" of the system ──►  ~/elcaciquedeck-data/twin/<date>/
   • folders & files (names, sizes)                         snapshot.json + screenshots/
   • drives (lsblk, df), servers (status, docker ps)                 │
   • what each command printed that day                              ▼
   • screenshots of each Cacique web page                El Cacique Admin desktop
   • settings with passwords MASKED                      (Files · Terminal · Browser · Disks · Dash)
```

1. **Snapshot** (`tools/snapshot.sh`, run automatically at the end of `update.sh`):
   - Folder tree of the repo and the top levels of Library and Vault (**names only, no file contents**).
   - Real outputs of `lsblk -f`, `df -h`, `status.sh`, `docker ps`, `ip route get`, `groups`, etc.
   - Each `.env` with **every password replaced by `••••••`**.
   - Screenshots of each Cacique page, taken with Firefox in headless mode.
   - Stored **only on the laptop**, in `~/elcaciquedeck-data/twin/`. **Never uploaded to GitHub.**
2. **The twin** (a web page served by the Home Lab, like CaciqueAcademy today):
   - A **login screen** → "El Cacique Admin".
   - A **desktop** with a dock: **Files**, **Terminal**, **Firefox**, **Disks**, **CaciqueDash**, **Settings → Network**.
   - The **Terminal** answers using the real outputs captured in the snapshot, so `ls /media/$USER/Library`
     shows what was really on the drive that day.
   - **Firefox** opens the real screenshots of each Cacique page; links between them work.
3. **Time machine:** every update keeps a snapshot, so the game can show *"your deck on Nov 1"* vs *"after the
   Vault move"* — you can see how the lab grew.

## The game part / El juego
- **Incidents** are layered onto the twin, based on real failures: "Vault got unplugged", "CaciqueDocs is red (500)",
  "port 8080 is busy", "a drive is FAT32", "Docker permission denied". The player diagnoses using the same apps
  they'd use for real (Files, Disks, Terminal, Firefox), and the Field Manual is one click away.
- **Levels:** Visitor (look around) → Helper (find information) → Technician (diagnose) → Cacique (fix and verify).
- **Ages:** a kid mode with point-and-click tasks ("find the movies folder"), and an adult mode with the Terminal.
- **Progress** saved per player (once family accounts exist, per account).

## Safety rules / Reglas de seguridad
- The twin is **read-only practice**: nothing in it can touch the real system.
- **No passwords, no private file contents, no document names from Vault** (only counts and sizes).
- Served only inside the home network; once family accounts exist, the admin twin is **adults only**.

## Build phases / Fases
1. **Snapshot tool** (`tools/snapshot.sh`) + hook into `update.sh`; verify nothing private is captured.
2. **Desktop shell**: login, dock, Files app and Terminal reading the snapshot.
3. **Firefox + Disks + Dash** apps using screenshots and captured data.
4. **Incidents engine** reusing CaciqueAcademy's 7 missions, then new ones.
5. **Time machine** and kid mode.

## ▶️ Pick up here
> "Let's build CaciqueAcademy 2.0 phase 1 from docs/academy-twin-plan.md."
