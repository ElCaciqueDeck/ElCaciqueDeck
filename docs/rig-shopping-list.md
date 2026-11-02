# 🛒 ElCaciqueDeck — Full Rig Shopping List (closet build, Omada)

> **Status: PLAN.** Location: a dry, cool, flood-safe **closet inside the house**. No Faraday cage, no shed, no fiber.
> Network brand: **TP-Link Omada** (one dashboard for router, switches and Wi-Fi).
> *Prices change constantly; ask Claude for a priced checklist before buying.*

---

## A. Compute — the 10" rack
| Qty | Item | Spec to look for | Why |
|---|---|---|---|
| 3 | **Lenovo ThinkCentre M720q (Tiny)** | Intel i5-8500T / 9500T, **16 GB DDR4** (laptop-size SODIMM), **1 TB NVMe SSD**, power brick included | The 3-node Proxmox cluster (1 head + 2 workers). Must be the **"q" Tiny** to fit a 10" rack |
| 3 | 10" 1U mounting bracket for Lenovo Tiny | Made for M720q/M920q | Holds each node in the rack |
| 3 | Extra 16 GB DDR4 SODIMM *(optional, later)* | Same speed as installed | Takes each node to 32 GB |

## B. Storage — NAS
| Qty | Item | Spec | Why |
|---|---|---|---|
| 1 | **2- or 4-bay NAS** (Intel-based; can run TrueNAS or the maker's OS) | Intel N100 class or better, 2.5 GbE port | Replaces the USB drives; drives stay connected and are monitored |
| 2 (min.) | **NAS hard drives (CMR, NAS-rated)** | 8 TB+ each, **mirrored** (RAID 1) | Library + Vault on protected storage; one drive can die without losing anything |
| — | Your 2× 2 TB Seagates | — | Become **backup drives**: one at home, one **off-site** (3-2-1 rule) |

## C. Network — Omada
| Qty | Item | Example model | Why |
|---|---|---|---|
| 1 | **Omada gateway (router/firewall)** | **ER707-M2** (2.5 GbE) | VLANs, firewall rules, DHCP reservations. Sits after the Deeper Mini |
| 1 | **Omada managed PoE switch** | **SG2210XMP-M2** (8× 2.5 GbE PoE+, 2× SFP+) | Connects rack, NAS and powers the Wi-Fi access points over the cable |
| 2–4 | **Omada ceiling access points** | **EAP650** (Wi-Fi 6) or **EAP670** (faster) | One per area; each broadcasts Cacique-Familia / Adultos / IoT |
| 1 | **Omada controller** | **OC200** hardware, *or* free software controller in Docker on the rig | The single dashboard for all Omada gear |
| — | Modem → **Deeper Connect Mini** | (already owned) | Ad blocking on the internet path |

## D. Rack & power
| Qty | Item | Spec | Why |
|---|---|---|---|
| 1 | **10" open-frame rack, 8U–12U** | DeskPi RackMate T1/T2 class | Small, ventilated, closet-friendly |
| 2–3 | 10" rack shelves (1U) | Vented | Gateway, switch, NAS, controller |
| 1 | 10" patch panel, 12-port, keystone | Cat6 | Clean termination of house cables |
| 1 | 10" power strip (PDU) | Surge-protected | Power inside the rack |
| 1 | **UPS, pure sine wave, 1000–1500 VA** | With **USB port** | Rides through outages; **NUT** shuts servers down safely |
| 1 | Whole-closet surge protector | — | Lightning season protection |

## E. Cabling & tools (materials)
| Qty | Item | Notes |
|---|---|---|
| 1 box | **Cat6, solid copper (NOT "CCA")**, 500–1000 ft | Runs from the closet to each access point and TV |
| 20+ | Cat6 keystone jacks + wall plates | One per room drop |
| 1 set | Punch-down tool, RJ45 crimper, **cable tester** | Test every run before closing walls |
| 10–20 | Short patch cables (0.5–1 ft) Cat6 | Inside the rack |
| — | Low-voltage wall brackets, fish tape, drywall saw, cable clips | For in-wall runs |
| — | Velcro straps, **labels/label maker** | Every cable labeled at both ends |

## F. Closet environment (indoor)
| Qty | Item | Why |
|---|---|---|
| 1 | **Thermostat-controlled exhaust fan** (pushes hot air out of the closet) | Closets trap heat; this is the #1 need |
| 1 | Louvered door or door vent | Fresh air in |
| 1 | **Zigbee USB coordinator** for CaciqueHome | Lets Home Assistant read cheap sensors |
| 2 | Temperature/humidity sensors (Zigbee) | Alerts at > 30 °C or > 60 % humidity |
| 1 | Water-leak sensor (Zigbee) | Under the rack |
| 1 | Smoke detector + small **Class C** fire extinguisher nearby | Electrical safety |
| 1 | Small dehumidifier *(only if humidity stays > 60 %)* | Puerto Rico humidity |

## G. Emergency / maintenance kit
| Qty | Item | Why |
|---|---|---|
| 1 | Small portable monitor + compact keyboard ("crash cart") | Fix a node when the network is down |
| 2 | USB sticks (32 GB+) with **Ventoy** | Install/repair: Proxmox, Ubuntu, memtest |
| 1 | Spare 1 TB NVMe SSD | Swap a failed node drive quickly |
| — | Printed copy of the **Field Manual** + network plan | Works with zero electricity |

## H. Gaming node (beside the rack, not in it)
See the i7 "build once" list: **i7-14700K · Z790 Mini-ITX with 2.5 GbE · 32 GB DDR5 · RTX 5070 Ti 16 GB · 2 TB NVMe · 850 W SFX · 280 mm AIO · Cooler Master NR200P** — runs **Bazzite**, streams with **Sunshine → Moonlight**.

## I. Software (all free)
Proxmox VE · TrueNAS (or NAS OS) · Omada Controller · Ubuntu Server · Docker · everything already in this repo · Bazzite · NUT.

---

## ▶️ Pick up here
> "The rig parts are here: [list]. Let's start with the network (docs/network-plan.md step 1), then Proxmox."
