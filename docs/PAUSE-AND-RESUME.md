# ⏸️ El Cacique — paused (Nov 5, 2026) · how to pick it back up

> **Status: PAUSED on purpose.** The software is done and proven. The IdeaPad S340 (2018) ran the whole system and
> showed its limits (≈76 °C and ≈65% memory with nobody using it), so it's switched off until the real hardware arrives.
> *Proyecto en pausa: el software está listo; esperamos el equipo.*

## Where we stopped
| Area | State |
|---|---|
| Installer (`install.sh` + window) | ✅ Works on a fresh Ubuntu 26.04 computer (proven on the IdeaPad, Nov 3) |
| Apps | ✅ Flix, Photos, Docs, Library, Arcade, Home, Guard, Vault, Calendar, Sync, Finanzas (+coach), Cams, Guía; Office ready for 12 GB+ machines |
| Front page | ✅ Aero Naturaleza design, Familia / Invitado views (merged to `main`) |
| CaciqueGauges (:8888) | ✅ Aero health page, always-on service; first look on the IdeaPad still to confirm (reload the tab) |
| Drives | ✅ Library + Vault mount at `/media/<user>/…` at power-on (fstab by label) |
| Still open | ⬜ Phone couldn't open the front page ("taking too long"); ⬜ account tests with ElCaciqueAdmin + Jay; ⬜ reserve the server's address in the router |

## The hardware plan (decided Nov 5)
**4 new computers:**
- **3 servers:** Lenovo ThinkCentre M720q (i5, 16 GB) = the Proxmox cluster (1 head + 2 workers). `docs/rig-shopping-list.md`
- **1 command computer:** the station the Home Lab is run from; also an extra machine alongside the 3 servers.

**Network base first:**
- **Chain:** Liberty (bridge mode) → **Deeper Mini** → **TP-Link ER605** → **TL-SG108E**, with UE300C adapters for the wired links. `docs/network-plan.md`
- **The rest of the house:** the living-room router goes to AP mode; the second-apartment line stays outside the Home Lab.

**Rack:** 10" 12U on wheels, filled in phases. `docs/rack-layout.md`

**Other uses:**
- **IdeaPad:** a spare / test bench.
- **ThinkPad L540:** the field deck (The Base + The Overkill stick). `docs/cyberdeck-plan.md`

## To turn the IdeaPad back on (any time)
1. Power on and log in. CaciqueGauges starts by itself (http://<laptop>:8888).
2. `bash ~/elcaciquedeck/start-all.sh`
3. `bash ~/elcaciquedeck/status.sh`

## ▶️ Pick up here
> "The hardware is here: [list]. Let's resume from docs/PAUSE-AND-RESUME.md."

Order when we resume:
1. **Network base** (Deeper + ER605 + switch), with fixed addresses.
2. **Fix the phone access** on the new network.
3. **Proxmox** on the 3 M720q.
4. **Run the installer** in the cluster (Level 3).
5. **Account tests** (ElCaciqueAdmin + Jay).
6. **Family logins.**
7. **Start the 90-day test**, then the public release.
