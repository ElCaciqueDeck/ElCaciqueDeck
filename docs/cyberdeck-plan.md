# 🛰️ Cacique Field Deck — the scout's mobile station (ThinkPad L540)

> **Status: DESIGN (Nov 2026).** The ThinkPad L540 leaves home-lab duty (the IdeaPad takes over) and becomes a
> **field deck**: a mobile station for a scout on an e-bike with a drone, a radio and this laptop.
> *Estado: diseño. La ThinkPad deja de ser servidor y se convierte en estación móvil de campo.*

## Home lab ≠ field deck
| | Home lab (IdeaPad) | Field deck (ThinkPad) |
|---|---|---|
| Job | Serve the family: media, photos, documents, home | **See, coordinate and record** in the field |
| Network | Always on, many devices, easy names | **Silent by default**; transmits only when you choose |
| Power | Wall + UPS | Its battery, a spare battery, the e-bike, solar |
| Data | Shared with the family | **Encrypted**, private, synced home only when back |
| Software | Docker apps | Base: Ubuntu + field toolkit · Overkill: Kali Live stick |

## Two modes on one laptop (decided)
| | 🟢 **The Base** | 🔴 **The Overkill** |
|---|---|---|
| What | The friendly **command station**: listen, map, plan, coordinate | A **full ethical-hacking + privacy system** in a pocket bag |
| How it starts | Normal power-on (internal drive → SSD later) | Plug the Overkill stick, restart, pick it in the boot menu (F12) |
| System | **Ubuntu** (stable, same family as the home lab) | **Kali Linux Live + encrypted persistence** (all tools and settings kept on the stick) |
| Internal drive | In use | **Not mounted** — the Base is untouched and Kali leaves no trace on it |
| Radios | EMCON modes (SILENT / MESH / LINK) | Same modes + only the links you choose |
| Data | Encrypted home folder | Encrypted persistence; a small encrypted **"drop"** area to pass files to/from the Base |

### 🟢 The Base (Ubuntu) — listen, don't judge
| Piece | Choice | Role |
|---|---|---|
| Laptop | ThinkPad L540 (SSD + 16 GB later) | Maps, TAK server, LoRa bridge, SDR, drone ground station, logbook |
| Situational awareness | **ATAK-CIV on a cheap Android (no SIM)** + **OpenTAKServer** | Shared map: positions, markers, routes, photos, chat |
| Off-grid mesh | **Meshtastic** LoRa nodes (915 MHz) | Encrypted text + positions, no towers |
| Drone | **ArduPilot / PX4 (MAVLink)** | QGroundControl; drone on the TAK map |
| Radio | **GMRS** (not bought yet) | Team voice |
| Listening | **RTL-SDR (receive only)** | Spectrum, aircraft, weather, sensors |
| References | Kiwix: medical + survival | Offline |

### 🔴 The Overkill — the pocket bag
| Item | Role | Notes |
|---|---|---|
| **Overkill stick** (256 GB) | Kali Live + **LUKS-encrypted persistence** (boot option "USB Encrypted Persistence") | Prefer a fast **USB 3.2 stick or tiny USB SSD** (e.g. Samsung FIT Plus / Bar Plus, SanDisk Extreme Pro). A microSD in a reader works but is **slower and wears out** with a full OS on it — if used, pick an A2/V30 card and keep a backup image |
| Optional **ghost stick** (16–32 GB) | **Tails** — anonymous internet through Tor, forgets everything at shutdown | Keep Tails on **its own stick**: Tails can't hold Kali's tools, and mixing them weakens Tails' protection |
| **Deeper Connect Pico** | Small inline hardware firewall/VPN (Ethernet in → Ethernet/Wi-Fi out, USB-C powered, 1 W) | Use only in **LINK** mode: laptop → Pico **by cable**, Pico → the upstream (a router or travel router). **Turn off its bandwidth-sharing / mining** in the field, so your link doesn't carry strangers' traffic. A VPN gives privacy, **not** anonymity — that's Tails/Tor's job |
| **Ledger Nano** | Crypto wallet **+ hardware security key** | Ledger's *Security Key* app (FIDO2/U2F) protects logins; its *OpenPGP* app holds signing/encryption keys. The 24 words live **only on paper/steel**, never typed into any computer |

**The drop:** the Overkill stick also gets a small separate encrypted partition (LUKS) that **both** systems can open
with its passphrase — the only bridge between the Base and the Overkill (field notes, captures, photos).

**Emergency:** Kali's **nuke passphrase** destroys the encryption keys of an encrypted partition at boot
(we test it on a copy before trusting it). Keep an encrypted backup of the stick's LUKS header at home.

## How it fits together
```
      [Drone]  --915 MHz telemetry-->  [SiK radio]--USB--+
                                                         |
  [Team Meshtastic nodes] ~~LoRa~~ [Deck's LoRa node]--USB-+--> ThinkPad (Base: Ubuntu  ·  Overkill: Kali stick)
                                                         |      - OpenTAKServer  (the shared map)
      [Android with ATAK-CIV] ------- USB cable --------+      - TAK<->Meshtastic gateway
            (no SIM, Wi-Fi/BT off)                      |      - MAVLink -> TAK bridge (drone on the map)
                                                         |      - QGroundControl (fly / plan / watch)
      [GPS puck] --USB-- (receive only)  ---------------+      - SDR: spectrum, aircraft, weather, sensors
      [RTL-SDR]  --USB-- (receive only)  ---------------+      - offline maps of Puerto Rico + elevation
                                                                - Field logbook (everything time-stamped)
   [GMRS handheld]  voice with the team (separate)            - Kiwix: medical + survival references
```
The Android talks to the deck **by USB cable** (reverse tethering), not Wi-Fi or Bluetooth: no extra radio signal.

## Staying hidden: transmission discipline ("EMCON")
Anything that transmits can be found. Receiving (GPS, SDR, listening) can't. The deck gets a single command and a
top-bar indicator with three modes:

| Mode | What transmits | Use |
|---|---|---|
| 🔴 **SILENT** | **Nothing.** Wi-Fi + Bluetooth hardware-off (`rfkill`), LoRa node set to *receive only* (`lora.tx_enabled = false`), no drone telemetry uplink | Observe: GPS, SDR, maps, logbook, listen to the mesh |
| 🟡 **MESH** | Only short encrypted LoRa bursts when *you* send; no automatic position beacons | Coordinate with the team quietly |
| 🟢 **LINK** | Wi-Fi allowed (home network / known access point) | Sync to the home lab, updates |

Plus, always:
- Random Wi-Fi/Bluetooth hardware addresses (MAC), generic computer name, no auto-join of networks.
- No cloud accounts, telemetry or auto-updates on the deck; updates only in LINK mode at home.
- Android: no SIM, Google location off, airplane mode, lives in a **Faraday pouch** when not in use.
- Night mode: red screen filter, keyboard light off, LED covers.
- Online, when needed: Tor Browser (or the Tails USB later) — never your home identity.

## What the deck can sense (receive only, legal)
With one **RTL-SDR v4** and a small antenna kit:
- **Spectrum view** (SDR++): which bands are busy around you — radios nearby show up as activity.
- **Aircraft** (ADS-B, `readsb` + `tar1090`): planes and helicopters on an offline map.
- **Weather**: NOAA weather radio, weather satellites (SatDump), nearby weather stations (`rtl_433`).
- **Public radio**: FRS/GMRS/marine/NOAA channels in the clear.
- **Wi-Fi/Bluetooth survey** (Kismet, passive): how many devices are around, what networks exist —
  awareness only, nothing is joined or attacked.

## The drone (ArduPilot / PX4)
- **QGroundControl** on the deck: missions, geofence, return-to-home, live telemetry, offline maps.
- A **SiK 915 MHz telemetry radio** pair for the link (it transmits → MESH/LINK modes only; the drone can fly a
  pre-planned mission with the uplink off).
- A small **MAVLink → TAK bridge** (we write it with PyTAK) puts the drone on everyone's ATAK map.
- Photos/video come back to the deck's encrypted store and appear on the map where they were taken.

## Ethical-hacking toolkit (Overkill stick; own systems / with permission only)
Kali covers it: Nmap, Wireshark, Kismet, Bettercap, Aircrack-ng suite, Metasploit, Burp, Hashcat… plus an
**Alfa** USB Wi-Fi adapter for monitor mode. Practice targets: **our own home lab**, our own test router, and
intentionally vulnerable practice machines. A "lab notebook" template records scope, permission and findings.

## Power on the move
| Source | How |
|---|---|
| Internal battery | ThinkPad L540 battery is **removable** → carry a charged spare (hot-swap in the field) |
| E-bike battery | Through a **portable power station** (charged from the bike's charger / solar) or a fused DC-DC converter to 20 V with a Lenovo "slim tip" plug |
| Solar | 100 W folding panel → power station |
| Saving power | SILENT mode, screen dim, CPU power-saver profile, SDR/drone links only when used |

## Make the L540 field-ready
- **Swap the hard disk for an SSD** (vibration on a bike kills spinning disks) — and it gets much faster.
- **16 GB RAM** (2 slots) for the TAK server + SDR + QGroundControl at the same time.
- Hard case with foam (Pelican-style), rain cover, short right-angle USB cables, a powered USB hub.
- GPS: a USB **u-blox** puck (receive-only).

## Shopping list (approximate, verify prices)
| Item | Why | ≈ USD |
|---|---|---|
| 1 TB SATA SSD | Vibration-proof, fast | 60 |
| 2×8 GB DDR3L SO-DIMM | 16 GB | 30 |
| Spare L540 battery | Field hours | 40 |
| Cheap Android (Android 10+, no SIM) | ATAK-CIV | 80–150 |
| 256 GB fast USB stick / mini USB SSD | Overkill stick | 30–60 |
| 32 GB USB stick | Tails ghost stick (optional) | 10 |
| 3–4 Meshtastic nodes (e.g. RAK WisBlock or Heltec V3) + antennas | Team mesh | 30–60 each |
| RTL-SDR Blog V4 + dipole kit | Receive-only awareness | 45 |
| u-blox USB GPS | Position without transmitting | 20 |
| SiK 915 MHz telemetry pair | Drone link | 40–60 |
| Alfa AWUS036ACM (or similar) | Wi-Fi testing, monitor mode | 40 |
| GMRS handhelds ×2 (Part 95 certified) + GMRS license | Team voice | 2×60 + 35 |
| Faraday pouch (phone/tablet) | Hide the Android | 20 |
| Power station + 100 W solar | Power in the field | 250–400 |

## Legal lines (so the deck stays a tool, not a problem)
- **Listening** to the clear radio spectrum is legal; **intercepting cellular calls or decoding private
  encrypted communications is not** — the deck doesn't do it.
- **Transmitting**: LoRa/Meshtastic (ISM 915 MHz) and SiK radios need no license; **GMRS needs a license**
  (no exam, covers the family); ham bands need an exam. **Jamming is illegal**, period.
- **Drones**: FAA rules — register the drone, keep **Remote ID on**, stay below 400 ft, out of restricted
  airspace (check B4UFLY / the FAA map). Not recreational → Part 107 certificate.
- **Wi-Fi/network testing** only on our own equipment or with written permission.
- Recording people: follow Puerto Rico privacy law; don't publish others' data.

## Build phases
1. **Base** — Ubuntu (encrypted home folder), MAC randomization, `deckmode silent|mesh|link`, field logbook,
   offline maps of Puerto Rico + elevation; SSD + 16 GB when bought.
1b. **Overkill stick** — Kali Live + encrypted persistence + drop partition + nuke test; field toolkit
   preinstalled; optional Tails ghost stick; Deeper Pico set up for LINK (sharing off); Ledger security-key apps.
2. **Awareness** — RTL-SDR stack (SDR++, ADS-B map, rtl_433, SatDump), GPS (gpsd), Kismet passive survey.
3. **Team picture** — Meshtastic nodes, OpenTAKServer, TAK↔Meshtastic gateway, ATAK-CIV on the Android over USB.
4. **Drone** — QGroundControl, SiK link, MAVLink→TAK bridge, photo geotag import.
5. **Power & case** — power station, solar, spare battery, hard case.
6. **Training** — field drills: SILENT patrol, MESH check-ins, drone survey, ethical-hacking lab on the home lab.

## ▶️ Pick up here
"Let's build Field Deck phase 1 from docs/cyberdeck-plan.md." (after the IdeaPad home lab is running)
