# 🌐 ElCaciqueDeck — Network & Shed Plan (VLANs)

> **Status: PLAN ONLY.** Nothing here is installed yet: it needs hardware.
> When the hardware arrives, start at **"Pick up here"** at the bottom.
> *Estado: SOLO PLAN. Cuando llegue el equipo, empezar en "Pick up here".*

---

## 1. The goal / La meta
One home network that is **private, separated and works without internet**:
kids and guests only reach the Home Lab, smart devices never touch the internet,
adults have full internet, and the rig lives in a protected shed.

*Una sola red de la casa, privada y separada, que funciona sin internet.*

---

> **Update 2026-11-01:** the rig goes in a **dry, cool closet inside the house** (no shed, no fiber, no Faraday cage),
> and the network brand is **TP-Link Omada**. The Omada gateway (ER707-M2) takes the firewall role below;
> OPNsense stays an option. Full parts list: `docs/rig-shopping-list.md`.

## 2. Physical layout / Recorrido físico

```
 Internet cable
      │
   [Modem] ── (bridge mode if possible)
      │
 [Deeper Connect Mini]           ← ad blocking for the internet path
      │
 [Gateway/firewall: Omada ER707-M2]  ── in the rack (closet)
      │  (one cable carries all VLANs = "trunk")
 [Managed switch, VLAN + SFP]  ─── in the rack
      │            │
      │            └── Home Lab servers (3× ThinkCentre M720q), gaming node, UPS mgmt
      │
   Cat6 runs inside the walls (closet → each room)
      │
 [Omada ceiling access points, PoE]  ── one per area; each broadcasts all SSIDs
```

**No Wi-Fi in the closet.** Everything there is wired. The switch powers the access points over the same cable (PoE).

---

## 3. The VLANs / Las redes

| VLAN | Name | Subnet | Who | Internet | Wi-Fi name (SSID) |
|---|---|---|---|---|---|
| 10 | **Management** | 10.10.10.0/24 | Firewall, switches, APs, admin laptop | Updates only | *(none — wired only)* |
| 20 | **Servers** | 10.10.20.0/24 | Home Lab rig, gaming node | Outbound only (updates, metadata) | *(none — wired only)* |
| 30 | **Familia** | 10.10.30.0/24 | Kids, guests, family devices | ❌ Home Lab only (+ optional allow-list) | `Cacique-Familia` |
| 40 | **Adultos** | 10.10.40.0/24 | Adults' phones and computers | ✅ Full (through Deeper Mini) | `Cacique-Adultos` |
| 50 | **IoT** | 10.10.50.0/24 | Hue Bridge, TVs, smart plugs | ❌ None | `Cacique-IoT` (hidden) |

Fixed addresses (set as DHCP reservations in OPNsense):

| Device | Address |
|---|---|
| Firewall | 10.10.10.1 (and .1 on every VLAN) |
| Rig head node / front page | 10.10.20.10 |
| Rig worker nodes | 10.10.20.11, 10.10.20.12 |
| Gaming node | 10.10.20.20 |
| CaciqueGuard (DNS) | 10.10.20.53 |
| Hue Bridge | 10.10.50.10 |

---

## 4. Firewall rules (who may talk to whom) / Reglas

| From ↓ / To → | Management | Servers | Familia | Adultos | IoT | Internet |
|---|---|---|---|---|---|---|
| **Management** | ✅ | ✅ | ✅ | ✅ | ✅ | updates |
| **Servers** | ❌ | ✅ | ❌ | ❌ | ✅ *(CaciqueHome → Hue)* | outbound |
| **Familia** | ❌ | ✅ *web ports only* | ✅ | ❌ | ❌ | ❌ *(allow-list optional)* |
| **Adultos** | ❌ | ✅ *web ports only* | ❌ | ✅ | ✅ *(control TV/lights)* | ✅ |
| **IoT** | ❌ | ✅ *(only to CaciqueHome)* | ❌ | ❌ | ✅ | ❌ |

- **DNS:** Familia and IoT use **CaciqueGuard (10.10.20.53)**, so `cacique.home` works everywhere with no settings on the device.
  Adults use CaciqueGuard too; it forwards internet names onward.
- **Phones casting to TVs** across VLANs needs an **mDNS repeater** (OPNsense plugin) — enable only between Adultos ↔ IoT.
- **Admin pages** (CaciqueGuard, Home Assistant settings, OPNsense) are reachable **only from Management**.

---

## 5. Hardware shopping list / Lista de equipo
| Item | What to look for | Notes |
|---|---|---|
| **Firewall** | Small fanless PC with **4× Intel 2.5 GbE** ports (Intel i226), 8 GB RAM, small SSD | Runs **OPNsense** (free) |
| **Rack switch** | **Managed** (802.1Q VLANs), **SFP/SFP+** port for fiber, 8–16 ports | e.g. TP-Link Omada or UniFi |
| **House switch** | Managed, **SFP** port, **PoE** (powers the access points) | |
| **Fiber link** | 2× SFP modules + fiber cable of the right length (multimode for < 300 m, single-mode for longer) | Run in conduit, buried |
| **Wi-Fi access points** | Ceiling or wall APs with **multiple SSIDs + VLAN tagging**, PoE powered | Same brand as switches (Omada or UniFi) for one control page |
| **UPS** | Pure sine wave, with a **USB/network port** | For automatic safe shutdown (NUT) |
| **Surge protection** | Whole-shed surge protector + grounded rack | Lightning is the #1 risk |

---

## 6. The shed / La caseta
| Need | Plan |
|---|---|
| **Hurricanes / floods** | Concrete or hurricane-rated, **raised off the ground**, equipment on the rack, never the floor |
| **Heat** | Mini-split sized for the room + equipment heat; target 20–26 °C |
| **Humidity** | Dehumidifier, target 40–55 % |
| **Dust** | Air purifier + filtered intake |
| **Sensors** | Temperature, humidity, water-leak, door → **CaciqueHome** → alerts (also over **Meshtastic** when the internet is down) |
| **Power** | Grid → **UPS** → (later) **solar + battery** → generator backup; **NUT** shuts servers down cleanly before the battery runs out |
| **Lightning** | **Fiber** between buildings, surge protection, grounding |
| **Off-site copy** | A third copy of **Vault** outside the property (3-2-1 rule) |

---

## 7. Order of build / Orden
1. Firewall + rack switch, **flat network first** (everything works like today).
2. Create VLANs one at a time: **Management → Servers → IoT → Familia → Adultos**. Test after each.
3. Access points with all SSIDs. Move devices network by network.
4. Fixed addresses → update `homepage/setup-homepage.sh` with the head node address.
5. Fiber + shed (when the building is ready).
6. UPS + NUT safe shutdown, then solar.

---

## ▶️ Pick up here / Retomar aquí
When the hardware arrives, tell Claude:
> "The network hardware is here: [firewall model], [switch model], [AP model]. Let's start step 1 of docs/network-plan.md."

Claude will then write the OPNsense VLAN setup, the switch port map and the AP settings as step-by-step,
one-command-per-box guides, plus updates for CaciqueGuard and the Homepage.
