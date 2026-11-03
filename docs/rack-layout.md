# 🗄️ ElCaciqueDeck — Rolling Rack Layout (buy once, grow slowly)

> **Status: PLAN (Nov 2026).** One **10-inch, 12U open-frame rack** sitting on a **rolling base with locking casters**.
> No wall mounting: it rolls, and with the top handle it can be carried. It holds today's gear and the final rig
> (`docs/rig-shopping-list.md`), so nothing gets bought twice.
> *Estado: plan. Un rack de 10" y 12U sobre ruedas: hoy guarda lo que tenemos y mañana el rig final.*

## Why 10-inch, 12U
- The final rig was designed for 10": 3× Lenovo **M720q Tiny**, Omada gear, a small NAS.
- Light enough to carry (with a top handle) and narrow enough for a closet; **12U** leaves room for every phase.
- Open frame = good airflow (Puerto Rico heat). Keep the room/closet door closed so little hands stay out.

## The layout (top to bottom)
```
   ON TOP OF THE RACK (radios stay OUTSIDE the metal)
   ├─ Liberty modem/router (its Wi-Fi is the "old" network)
   ├─ Hue Bridge  ·  Zigbee USB stick (on a USB extension cable)
   └─ (later) Meshtastic base node, antenna cable to a window
 ┌──────────────────────────────────────────────────────────┐
 │ U1   Patch panel, 12-port keystone ............... Phase 2 │
 │ U2   Brush / cable-management panel .............. Phase 2 │
 │ U3   Shelf: main switch  TL-SG108E → Omada PoE switch (Ph 3)│
 │ U4   Shelf: ER605 router (+ Omada OC200 later) ... Phase 1 │
 │ U5   Shelf: Deeper Mini + 5-port switch (2nd apt line)  Ph 1│
 │ U6   M720q node 1 (head) ......................... Phase 4 │
 │ U7   M720q node 2 ................................ Phase 4 │
 │ U8   M720q node 3 ................................ Phase 4 │
 │ U9   ┐ Shelf: USB drives today (Library + Vault)   Phase 1 │
 │ U10  ┘ → 2/4-bay NAS later ....................... Phase 4 │
 │ U11  Spare (cameras NVR / field-deck dock / growth)        │
 │ U12  10" power strip (PDU, surge-protected) ...... Phase 1 │
 └──────────────────────────────────────────────────────────┘
   ROLLING BASE (locking casters)
   ├─ UPS tower, pure sine wave, 1000–1500 VA, USB (heaviest item lowest = stable)
   └─ IdeaPad on a vertical laptop stand (a 14" laptop is too wide for a 10" rack)
```
Until Phase 4, U6–U8 stay empty (or hold a blank/vent panel). When the M720q nodes arrive, the IdeaPad
steps down to backup/"crash cart" duty.

## Phases
| Phase | Buy | Result |
|---|---|---|
| **1 — Now** | 10" 12U open rack **with top handle** · 3× 10" vented 1U shelves (one 2U-tall space for drives) · 10" PDU · rolling base with **locking** casters · UPS tower · TP-Link ER605 · TL-SG108E · UE300C/UE300 · Cat6 patch cables · Velcro + labels | Today's network in one tidy, movable place, on battery backup |
| **2 — Tidy** | 10" 12-port keystone patch panel + Cat6 keystones · brush panel · Zigbee stick · temp/humidity + water-leak sensors | Clean cabling; CaciqueHome watches the rack |
| **3 — Omada** | Omada PoE switch (SG2210XMP-M2) · ceiling access points (EAP650/670) · OC200 or the free software controller · VIGI/Tapo cameras | Strong Wi-Fi through concrete; VLANs from `docs/network-plan.md`; CaciqueCams |
| **4 — Compute** | 3× M720q Tiny + 10" brackets · 2/4-bay NAS + mirrored NAS drives | The final 3-node rig + protected storage |

**Gateway note:** the **ER605** is an Omada router with 1 Gbps ports, which matches the 1 Gbps internet and
handles the VLANs. The **ER707-M2** in the final list only adds 2.5 GbE; it becomes an optional upgrade.

## Rules of the rack
- Heavy at the bottom, radios on top, **casters locked** whenever it's not moving.
- Every cable labeled at **both ends** (e.g. `LIBERTY→SW5`, `DEEPER→ER605`, `ER605→SW8`, `2ND-APT`).
- Unplug the network cables before rolling it more than a few feet; never move it while the UPS is beeping.
- The second-apartment line stays exactly as it is: Liberty → 5-port switch → that router (outside the home lab).

## ▶️ Pick up here
> "The Phase 1 rack parts are here. Let's assemble it from docs/rack-layout.md."
