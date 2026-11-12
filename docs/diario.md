# ☀️ Cacique Diario · el mensaje del día de la casa

> The home itself speaks: the photo frames, the TV when it's idle, the smart mirror, the kitchen in the morning and a
> welcome when someone arrives. Faith, family union, order, health, knowledge and courage, a little every day,
> backed by the example of the adults at home. *La casa habla, y el ejemplo de los adultos la respalda.*

**Rules this app keeps**
- The house's own screens and speakers only. Personal phones get messages **only through an app the person installed**
  (the Home Assistant app). Nothing is slipped into other apps or websites.
- **Bible verses and AI-written messages wait for an adult** in the approval page before any screen shows them.
- Shared screens (frames, TV, kitchen) only show messages meant for everyone. Personal messages ("Did you tell your wife
  you love her today?") only appear on that person's own screen (`?para=<person>`).
- Everything stays in the house. No internet needed after setup.

## How it works
| Piece | What it is |
|---|---|
| `diario/biblioteca/*.json` | The message library (7 themes, Spanish + English). Bible text: Reina-Valera 1909 + KJV (public domain) |
| `diario/caciquediario.py` | The server on **port 8097**: screen page, adults' page, API, nightly job |
| Nightly job (04:00) | Picks each person's messages (no repeats for 30 days), draws 2-3 **picture cards**, puts them in the **"Cacique Diario" album** in CaciquePhotos, removes cards older than 7 days |
| Adults' page `/admin` | **Por aprobar** (verses, AI) · **Hoy** · **Personas** · **Recordatorios** (trash day…) · **Mis mensajes** · **Ajustes** |
| Optional AI | If CaciqueGuía is running, it writes new messages each night; they wait in **Por aprobar** |

## Addresses (from any device at home)
| Screen | Address |
|---|---|
| TV / kitchen / tablet (shared) | `http://<server>:8097` |
| One person's screen | `http://<server>:8097/?para=<person>` |
| Smart mirror (black background) | `http://<server>:8097/?modo=espejo` |
| Spanish only / English only | add `&idioma=es` or `&idioma=en` |
| Change speed (seconds per message) | add `&segundos=30` |
| For CaciqueHome / the mirror (JSON) | `/api/hoy?para=<person>` · `/api/mensaje?para=<person>&idioma=es` |

## Set it up (IdeaPad or any El Cacique server)
1. `cd ~/elcaciquedeck && git pull`
2. `bash ~/elcaciquedeck/diario/setup-diario.sh` → it prints the addresses; the password is in `~/elcaciquedeck-data/accounts/diario-password.txt`
3. Open `http://<server>:8097/admin`:
   - **Por aprobar:** compare each verse with your Bible → *Aprobar* (or fix the words first).
   - **Personas:** add each person; tick their roles (esposo, esposa, padres, abuelos, hijos) and themes.
   - **Recordatorios:** trash day (Wednesday is already there), anything weekly.
   - **Ajustes:** paste the **CaciquePhotos key** (Immich → your picture → Account settings → API keys → New key)
     so the picture cards go to the album. Optional: a folder of your own nature photos for card backgrounds.

## Connect the screens
**Photo frames (Frameo frame or an old Android tablet)** — show the album with **ImmichFrame**:
1. Make a CaciquePhotos API key for the frame (read-only is enough) and note the album **"Cacique Diario"** (and/or the family album).
2. Frameo frame: enable ADB (Settings → About → Beta program), then from the IdeaPad: `sudo apt install -y adb`, `adb devices`,
   `adb install ImmichFrame.apk` (from ImmichFrame's GitHub releases). Set it as the home app. Details:
   https://immich-kiosk-docs.pages.dev/misc/frameo
3. In ImmichFrame: server `http://<server>:2283`, the key, and the album(s). Family photos and the day's cards mix together.

**TV when idle (onn 4K Pro / any Google TV)** — the screensaver shows the album:
- Install **Aerial Views** (free, open source) from the Play Store → set it as the screensaver → source: Immich →
  `http://<server>:2283`, key, album "Cacique Diario" (+ family album). Or the unofficial **Immich Android TV** app's screensaver.
- Samsung's own TV system is too closed for this; the stick on an HDMI port does the work.
- Kitchen/TV browser alternative: open `http://<server>:8097` full screen.

**Smart mirror** — two ways:
- Simple: a Raspberry Pi opens `http://<server>:8097/?modo=espejo` in Chromium kiosk mode (black page, white words).
- Full: **MagicMirror²** (clock, weather, calendar) + copy `diario/MMM-CaciqueDiario/` to `~/MagicMirror/modules/` and add:
  `{ module: "MMM-CaciqueDiario", position: "lower_third", config: { url: "http://<server>:8097", para: "familia" } }`

**CaciqueHome (kitchen voice, welcome home, phone notifications)** — copy what you need from
`diario/homeassistant-ejemplo.yaml` (a sensor + 3 automations: morning kitchen message on movement, 7:00 message
without a sensor, welcome-home notification through the Home Assistant app).

## Start / stop
`start-all.sh` starts it (also in light mode: it's tiny). `stop-all.sh` stops it. `status.sh` shows **CaciqueDiario**.
Nothing starts by itself at power-on.

## Shopping list
See `docs/diario-shopping-list.md`.
