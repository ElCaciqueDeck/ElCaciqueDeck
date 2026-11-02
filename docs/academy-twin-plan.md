# 🖥️ CaciqueAcademy 2.0 — "El Cacique Admin" (the Digital Twin)

> **Status: v1 BUILT** — snapshot tool, desktop (Files · Terminal · Firefox · Disks), Story Mode, Free Mode, Kids/Adults.
> *Estado: v1 CONSTRUIDA.* Open / Abre: `http://<laptop number>:8095/admin.html`

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

## Three ways to play / Tres formas de jugar
| Mode | What happens | Kids 🧒 | Adults 🧑 |
|---|---|---|---|
| 📖 **Story Mode / Modo Historia** | The full creation of El Cacique HomeLab, one chapter per milestone, **up to the current update** (13 chapters today: the dream → the rebel USB → Kiwix and FAT32 → busy port → CaciqueFlix → CaciqueDash → GitHub → Docker → easy names → Photos/Home/Arcade → the Vault and Error 500 → Manual + Academy → El Cacique Admin). | Point and click in Files, Firefox and Disks | Real commands in the Terminal |
| 🎲 **Free Mode / Modo Libre** | Log in and a **random problem** is waiting: diagnose, fix, verify. Based on real failures. | Vault unplugged · Library unplugged · the lost movie | Vault unplugged · Error 500 (owner) · port 8080 busy · Docker says no · Library unplugged · gauges went dark |
| 🧭 **Explore / Explorar** | Just look around the deck as it was at the last update. | ✔ | ✔ |

- **Kids** never see the Terminal and don't need a password. **Adults** sign in with the practice password `cacique`.
- Progress (chapters reached, problems fixed) is saved per browser; with family accounts it will be per account.
- **Every real update adds a Story chapter**: edit `STORY` in `academy/admin.html` when we push the update.
- New Free Mode problems go in `INCIDENTS` (same file): what breaks, the steps, and the kid version if it fits.

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
1. ✅ **Snapshot tool** (`tools/snapshot.sh` → `tools/snapshot.py`), run by `update.sh` (step 7/7); privacy tested.
2. ✅ **Desktop shell**: login, dock, Files and Terminal reading the snapshot.
3. ✅ **Firefox + Disks** using screenshots and captured data (pages without a picture are drawn).
4. ✅ **Incidents engine** (Free Mode, 6 adult + 3 kid problems) and **Story Mode** (13 chapters).
5. 🟡 **Time machine**: every snapshot is kept (newest 20) and the login screen lets you pick one once there are 2+.
   Still to do: side-by-side "before / after" view.
6. ⏳ Next ideas: CaciqueDash app, Settings → Network, more incidents (FAT32 drive, wrong IP typed,
   Paperless password capitals), per-account progress once family accounts exist.

## Files / Archivos
- `tools/snapshot.sh`, `tools/snapshot.py`: take the photo → `~/elcaciquedeck-data/twin/<date>/`.
- `adguard/Caddyfile`: serves `/twin/...` (read-only) next to the Academy on port 8095.
- `academy/admin.html`: the desktop, Story Mode (`STORY`), Free Mode (`INCIDENTS`).
- `academy/twin-demo/snapshot.json`: a made-up deck, used when there's no real snapshot (e.g. on GitHub).

## ▶️ Pick up here
> "Let's add the next Story chapter / a new Free Mode problem to El Cacique Admin."
