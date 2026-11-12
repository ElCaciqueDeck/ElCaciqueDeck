# 🛒 Cacique Diario · lista de compras (budget, in phases)

> Prices from reviews dated 2026; check at purchase (memory/RAM prices moved a lot this year). Start with what you own.
> *Empieza con lo que tienes; compra por fases.*

## Phase 1 · now (works with today's IdeaPad) — about $60–140
| Buy | Why | Price (approx.) |
|---|---|---|
| **onn 4K Pro (2026)** Google TV box, Walmart — **best pick** | Google TV, 3 GB RAM, 32 GB, Wi-Fi 6, remote finder. Installs Aerial Views / Immich TV for the idle-TV album. Reviewed as the best Google TV streamer of 2026. | **$59.98** |
| *Budget per extra TV:* **onn 4K** streamer | Same Google TV apps, less memory | ~$40 |
| *Premium option:* **Google TV Streamer** | Faster chip, 4 GB RAM, gigabit Ethernet | $99.99 |
| **Frameo 10.1" photo frame** from the tested list: Dxmart 10.1" HD, Yenock or Moonka ZN-DP1101 (Android 13, no root needed) | Runs ImmichFrame after enabling ADB, shows family photos + the day's cards | usually ~$50–80 |
| *Free alternative:* an old Android tablet + a stand | ImmichFrame app, same result | $0 |

❌ **Avoid:** the new **Fire TV Stick HD** (Amazon's Vega OS, can't install outside apps) and **Roku** (no Immich screensaver).
The Samsung TV's own system can't run it either; the stick goes in an HDMI port.

## Phase 2 · smart mirror (a weekend build) — about $240 with a used monitor
| Part | Price (approx.) |
|---|---|
| Raspberry Pi 4 (4 GB) — or a Pi 5 | $55 |
| Case with heatsinks | $14 |
| Official USB-C power supply | $9 |
| 64 GB microSD (A2) | $10 |
| Micro-HDMI → HDMI cable | $7 |
| 24" 1080p monitor (**used is fine**, or one you own) | $40–140 |
| Two-way **acrylic** mirror, ~18×30 in, 3 mm (lighter, safer than glass) | $70 |
| 1×3 pine (8 ft) + stain/paint | $22 |
| D-ring hangers + wire | $12 |
Software: Raspberry Pi OS + MagicMirror² (free) + `MMM-CaciqueDiario` (in this repo), or just Chromium kiosk on `/?modo=espejo`.

## Phase 3 · the kitchen voice and sensors
| Buy | Why | Price (approx.) |
|---|---|---|
| **Home Assistant Voice Preview Edition** | Speaker + microphones made for Home Assistant, works offline: says the morning message | $59 |
| Zigbee USB stick for CaciqueHome (one time) + motion sensor(s) | "When someone walks into the kitchen" triggers | stick + ~$15–30 per sensor |
| *Free alternative:* no sensor | Use the 7:00 AM automation instead (in `diario/homeassistant-ejemplo.yaml`) | $0 |
Phones: the **Home Assistant app** (free) for the welcome-home message, installed by each person who wants it.

## Total, in order
1. Phase 1: **onn 4K Pro** for the living-room TV ($60) → test the idle-TV album first.
2. Add a frame ($50–80) or reuse a tablet ($0).
3. Phase 2 mirror (~$240) when the cluster is in.
4. Phase 3 voice ($59) + sensors.

Sources: Android Authority onn 4K Pro (2026) review; Lon.TV 2026 streaming sticks compared; Immich Kiosk docs (Frameo
frames); Notebookcheck (Android TV screensavers for Immich); SpecPicks MagicMirror 2026 build; Home Assistant blog
(Voice Preview Edition).
