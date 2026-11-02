# 🧰 El Cacique Setup — the installer

> **Status: v1 built (Nov 2026)** — tested in practice mode (`--dry-run`); first real test: Jay's newer computer.

## For a new computer (anyone with Ubuntu)
1. Install **Ubuntu 22.04 or newer** (24.04 recommended).
2. Open the Terminal and type this **one line**:
   ```
   wget -qO- https://raw.githubusercontent.com/ElCaciqueDeck/ElCaciqueDeck/main/install.sh | bash
   ```
3. A gray step-by-step window opens (**El Cacique Setup**, also in the apps menu). Click **Next** until **Install**.

## The window, step by step
| Step | What happens |
|---|---|
| Welcome | Language (Español / English) |
| Your computer | Processor, memory, free disk, extra drives, network — and which levels it meets (✔ / ✘ and why) |
| Level | **1 Laptop**, **2 Deck**, **3 Lab** (a level the computer doesn't meet is greyed out; "advanced" allows it anyway) |
| Apps | Tick what to install (already-installed apps are marked and kept) |
| Drives | Level 1: everything in `~/elcaciquedeck-data`. Levels 2–3: pick the **Library** and **Vault** drives |
| Accounts | Admin name + password (default **ElCaciqueAdmin**), adults (login + nickname), Familia (PG), Invitado (PG-13) |
| Options | Start the servers by themselves at power-on (**off** by default), the computer's password |
| Summary → Installing → Done | Progress bar + every line of the install; at the end the family page address |

## The three levels
| Level | Minimum (checked automatically) | What you get |
|---|---|---|
| **1 · Laptop** | Ubuntu 22.04+, 4 threads, 8 GB memory, 40 GB free (the ThinkPad L540 is the baseline) | All the programs, on the computer's own disk — **no media, no big files** (a "mirror" of the deck) |
| **2 · Deck** | Level 1 + **one more drive** (ext4, 250 GB+, connected) | Library (movies, games, cameras) and Vault (documents, photos, passwords, calendar) on drives; **cameras** unlocked |
| **3 · Lab** | 8 threads, 16 GB memory, **two data drives** + a checklist: VLAN router/firewall, managed switch, UPS, ventilated closet | Everything; the VLANs and firewall are set on the Omada gear following [network-plan.md](network-plan.md) |

## The apps
| App | Program | Notes |
|---|---|---|
| CaciqueGuard | AdGuard Home + Caddy | `.home` names for every device; the first-time wizard is done for you |
| Cacique | Homepage | Shows **only the apps installed** on that computer |
| CaciqueLibrary | Kiwix | Field Manual included; encyclopedias are added later (big) |
| CaciqueFlix | Jellyfin (Flatpak) | First-time wizard done for you; Movies / Shows / Music libraries on Library |
| CaciqueDocs | Paperless-ngx | Admin made on first start; files owned by user 1000 (no more Error 500) |
| CaciquePhotos | Immich | Admin made for you; face recognition only with enough memory |
| CaciqueHome | Home Assistant | The admin becomes the owner; first-time setup finished |
| CaciqueArcade | RomM | First admin made; Familia/Invitado play with no login (kiosk mode) |
| CaciqueVault | Vaultwarden | https door + Cacique certificate (adults install it once per device) |
| **CaciqueCalendar** | Radicale | Family calendar **kept at home** (CalDAV: iPhone/Android/DAVx5); shared "Familia" calendar |
| **CaciqueSync** | Syncthing | Our own Dropbox: folder `Vault/Sync`; phones/computers pair with the Syncthing app |
| **CaciqueCams** | Frigate | Ring-style: any RTSP/ONVIF camera records **here**; recordings delete themselves after **90 days**. Level 2+ |
| **CaciqueGuía** | Ollama + our chat page | Local AI that answers **only about this Home Lab**; reads the status, the **logbook** and the Field Manual. Model picked by memory (3b / 7b / 14b) |

## The logbook (what the AI reads)
`tools/logbook.py` keeps one history of the Home Lab in `~/elcaciquedeck-data/logbook/` (JSON lines, passwords masked):
installer steps, every `[WARN]`/`[FAIL]` from setup reports, servers that are down, and a daily summary of the
CaciqueDash gauges. `start-all.sh`, `update.sh` and the installer write to it by themselves.
`python3 ~/elcaciquedeck/tools/logbook.py brief` shows what the AI sees.

## Files
- `install.sh` — the one-line start (git + python3-tk, download, menu shortcut, opens the window)
- `installer/cacique_installer.py` — the window (Tkinter, gray, bilingual)
- `installer/engine.py` — scan, levels, steps (`python3 installer/engine.py --dry-run` to practise)
- `~/elcaciquedeck-data/cacique.conf` — what was chosen (level, Library/Vault, apps, start at power-on)
- New: `calendar/`, `cameras/`, `guide/`, `paperless/setup-paperless.sh`, `tools/logbook.py`

## Not automatic yet / limits
- **VLANs and firewall** (Level 3) are a checklist + guide, not pushed to the Omada gear automatically.
- **Ring** itself only works through Ring's cloud; CaciqueCams works with cameras that give a local stream.
- First install needs internet and takes 30 min – 2 h (several GB).
- Practise first: `python3 ~/elcaciquedeck/installer/cacique_installer.py --dry-run`.
