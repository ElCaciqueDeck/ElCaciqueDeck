# 🛡️ Deeper Connect Mini · the first wall of the house

> Liberty modem → **Deeper Connect Mini (Virtual Wire / transparent)** → switch → living-room Archer (AP) + El Cacique.
> Later: Liberty (bridge) → Deeper → ER605 → switch, with CaciqueGuard (AdGuard) as the second layer for names.

## Settings (as of Nov 14, 2026)
| Area | Setting | Why |
|---|---|---|
| Firmware | 2.0.7.H2, auto-update on | Security fixes arrive by themselves |
| Mode | Virtual Wire (transparent) | Sits in the cable without changing the house network |
| DPN | Smart Route; backup tunnel West Europe / Germany #1 | Only chosen apps use other countries |
| App relocator / TV | Streaming stays **direct** (Netflix on a Japan route broke the Samsung TV) | Streaming apps check location |
| Web filter | Ads, trackers, malicious, parental control **on**; **DoH blocking on** | DNS filtering can't be skipped by browsers |
| HTTPS filter | **Off** (needs Deeper's certificate on every device; broke YouTube on the TV) | No one reads encrypted traffic |
| Bandwidth sharing | **On** (helps people reach open information) | Owner's choice |
| BT (torrent) sharing | **Off** | Strangers' torrents won't leave through our Liberty line |
| Logs | Weekly | — |
| Mining | Basic Mining 2.0 | Owner's own project; not advice |

## To do
- [ ] Stronger admin password (in the notebook, with the serial number - never on GitHub). A forgotten password needs
      Deeper support + the serial number.
- [ ] Routing → Domain Config → **Direct Route** for streaming, banking, Liberty, Proton and government sites.
- [ ] Cooling base when back in stock; meanwhile keep it raised with open air around it (46 °C / 115 °F at 7% CPU is fine).
- [ ] Watch "sessions": ~700 is normal; once it hit 32,768 (likely the device's maximum). If it climbs again, check the
      log for which device is opening so many connections.
- [ ] DPN app (paid subscription) only for phones/laptops away from home; at home the Mini already covers every device.
