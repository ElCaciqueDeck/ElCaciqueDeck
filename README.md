# 🇵🇷 ElCaciqueDeck: a Puerto Rican home lab

> **⚠️ For learning purposes only.**
> This is a home-based Puerto Rican project: a home lab built step by step by a **total beginner**.
> Everything here is shared as a learning journal. Use it at your own risk, adapt it to your own setup,
> and always understand a command before you run it.

---

## What this is

ElCaciqueDeck is an old Intel ThinkPad running **Ubuntu Linux**. It's being turned into a small,
self-reliant home server that works **without the internet**:

| Cacique name | Server | What it does | Easy address | Number address |
|---|---|---|---|---|
| 🧭 **Cacique** | Homepage | The family's front door: a button and status light for every server | `http://cacique.home` | `http://<laptop number>` (no port) |
| 📚 **CaciqueLibrary** | Kiwix | Offline encyclopedia: Wikipedia, wikiHow, iFixit, dictionaries, books (English and Spanish) | `http://caciquelibrary.home` | `:8080` |
| 🎬 **CaciqueFlix** | Jellyfin | Movies, series and anime the family owns | `http://caciqueflix.home` | `:8096` |
| 📄 **CaciqueDocs** | Paperless-ngx | Private document vault: scan, OCR (Spanish and English), tag and search | `http://caciquedocs.home` | `:8000` |
| 📸 **CaciquePhotos** | Immich | The family's own Google Photos: phone backup, albums, faces, search | `http://caciquephotos.home` | `:2283` |
| 🕹️ **CaciqueArcade** | RomM | Game library with box art; retro games play right in the browser | `http://caciquearcade.home` | `:8090` |
| 🏠 **CaciqueHome** | Home Assistant | Smart home and Philips Hue lights, working without internet | `http://caciquehome.home` | `:8123` |
| 🏎️ **CaciqueDash** | caciquedash.py | JDM-style gauges, plus a log reading every minute | `http://caciquedash.home` | `:8888` |
| 🛡️ **CaciqueGuard** | AdGuard Home | Gives every server its easy name, blocks ads for devices that use it | `http://caciqueguard.home` | `:3000` |

"Number address" = `http://<laptop number>:<port>`. It always works, even when the easy names don't.

Also on the deck: offline maps of Puerto Rico (Organic Maps) and Meshtastic (LoRa mesh radio, in progress).

**Single-laptop roadmap:** ✅ Docker → ✅ CaciqueDocs → ✅ CaciqueGuard → ✅ CaciquePhotos → ✅ CaciqueHome → ✅ Cacique Homepage → 🔧 CaciqueArcade

**Road ahead:** RTL-SDR radio listening, Meshtastic node, and a 3-node mini-PC Proxmox cluster in a 10" rack.

---

## 📁 Drive layout

```
Library (external drive)
├── Kiwix/                     ← all .zim files
├── Vault/paperless/           ← document vault (data, media, export, consume)
├── Photos/immich/             ← family photos and videos
├── Arcade/library/roms/<console>/   ← games (gb, gbc, gba, nes, snes, genesis, n64, psx, arcade...)
└── MEDIA/Jellyfin/
    ├── Movies/   Coco (2017)/Coco (2017).mkv
    ├── Series/   Show Name (2005)/Season 01/Show Name S01E01.mkv
    └── Anime/    Show Name (2005)/Season 01/Show Name S01E01.mkv
```

On the laptop's own disk (faster, not on the external drive):
```
~/elcaciquedeck-data/
├── immich-postgres/           ← CaciquePhotos database
└── homeassistant/             ← CaciqueHome settings
~/deck-logs/                   ← CaciqueDash minute-by-minute logs
```

---

## 🚀 One command for everything

```
bash ~/elcaciquedeck/start-all.sh     # start every server that's set up
bash ~/elcaciquedeck/status.sh        # which servers are up, and their addresses
bash ~/elcaciquedeck/stop-all.sh      # stop everything
```
The servers keep running after you close the Terminal. Logs: `~/elcaciquedeck/reports/run/`.

### First-time setup of each Docker server (once each, in this order)
Every setup script checks everything, prints `[ OK ]` / `[WARN]` / `[FAIL]`, and saves a report in
`~/elcaciquedeck/reports/`.
```
bash ~/elcaciquedeck/adguard/setup-adguard.sh               # CaciqueGuard + easy names
bash ~/elcaciquedeck/immich/setup-immich.sh                 # CaciquePhotos
bash ~/elcaciquedeck/homeassistant/setup-homeassistant.sh   # CaciqueHome
bash ~/elcaciquedeck/arcade/setup-arcade.sh                 # CaciqueArcade
bash ~/elcaciquedeck/homepage/setup-homepage.sh             # Cacique front page (run again if the laptop's number changes)
```
CaciqueDocs (Paperless) was set up by hand; see its section below.

---

## ▶️ Starting servers one by one (the manual way)

`start-all.sh` does all of this for you. To run one server by itself, use its own Terminal window
(**Ctrl+Alt+T**).
Stop any of them with **Ctrl+C** in its window.

**1. Kiwix (library)**
```
kiwix-serve --port 8080 /media/$USER/Library/Kiwix/*.zim
```

**2. Jellyfin (movies).** This deck uses the **Flatpak** version:
```
flatpak run org.jellyfin.JellyfinServer
```
Stop it with **Ctrl+C**, or from another window: `flatpak kill org.jellyfin.JellyfinServer`

**3. Dashboard** (also saves a reading every minute to `~/deck-logs/`)
```
cd ~/elcaciquedeck
python3 caciquedash.py
```

**4. Paperless-ngx (document vault).** Runs in the background with Docker:
```
cd ~/elcaciquedeck/paperless
docker compose up -d      # start
docker compose down       # stop
```
First-time setup: create the Vault folders on the Library drive, then create the private key
(it stays on the laptop and is never uploaded):
```
echo "PAPERLESS_SECRET_KEY=$(openssl rand -hex 32)" > .env
docker compose up -d
docker compose exec webserver createsuperuser
```

**5. CaciqueGuard + easy names (AdGuard Home + Caddy).** Runs in the background with Docker:
```
cd ~/elcaciquedeck/adguard
docker compose up -d      # start
docker compose down       # stop
```
First time only, run the setup script. It does everything and saves a report in `~/elcaciquedeck/reports/`:
```
bash ~/elcaciquedeck/adguard/setup-adguard.sh
```
Then finish in the browser at `http://localhost:3000`: admin page on port **3000** (not 80), DNS on port **53**,
create a login, and add one DNS rewrite: **`*.home` → the laptop number**.

**For the family (no settings to change):** the Cacique front page also opens at the plain laptop
number, `http://<laptop number>` (no port). On each phone: open it once → Share → **Add to Home Screen**.
It becomes a **Cacique** icon, and its buttons lead to every server. This needs the laptop's number to never
change (a fixed IP / DHCP reservation on the router).

**Using the easy names on another device:** set that device's DNS to the laptop number
(phone/PC Wi-Fi settings → DNS → manual). Devices that don't change keep working normally through the router.

**6. CaciquePhotos (Immich)**
```
cd ~/elcaciquedeck/immich && docker compose up -d    # start
cd ~/elcaciquedeck/immich && docker compose down     # stop
```
After setup: open `http://<laptop number>:2283`, create the admin account, then add family members
under Administration → Users. Phones: install the **Immich** app, server `http://<laptop number>:2283`,
turn on Backup. Smart search and faces only run if the laptop has 8 GB of memory or more.

**7. CaciqueHome (Home Assistant)**
```
cd ~/elcaciquedeck/homeassistant && docker compose up -d    # start
cd ~/elcaciquedeck/homeassistant && docker compose down     # stop
```
After setup: open `http://<laptop number>:8123` and create your account. Philips Hue appears by itself:
click it and **press the button on top of the Hue Bridge**.

**9. CaciqueArcade (RomM)**
```
cd ~/elcaciquedeck/arcade && docker compose up -d    # start
cd ~/elcaciquedeck/arcade && docker compose down     # stop
```
After setup: open `http://<laptop number>:8090`, create the admin account, then **Scan**. Add games by
copying them into `Library/Arcade/library/roms/<console>/` and scanning again. Retro games play inside the
browser of whoever is playing, so the laptop barely works. **Only legal games:** games you own and dumped
yourself, or free homebrew whose authors allow it (the first game, µCity, is open source under GPLv3).

Heavy consoles (PS2, GameCube/Wii, PS3, PS4) will run on the future gaming node (Bazzite + Sunshine) and
stream to any screen with Moonlight.

**8. Cacique front page (Homepage)**
```
cd ~/elcaciquedeck/homepage && docker compose up -d    # start
cd ~/elcaciquedeck/homepage && docker compose down     # stop
```
Buttons and look: `homepage/config/` (`services.yaml`, `settings.yaml`, `widgets.yaml`).
If the Homepage is off, the plain address shows a simple backup page instead.

---

## 🧰 Tools

**Arweave backup download** (`tools/arweave-backup.sh`): downloads a list of `https://arweave.net/...`
links, sorts each file by kind (Images, Videos, Audio, Documents, Data, Web, Archives, 3D, Other) with the
right file ending, and writes a `catalog.csv`. It can be stopped and re-run; finished files are skipped.
```
bash ~/elcaciquedeck/tools/arweave-backup.sh ~/my-links.txt
```
Saves to `Library/Backups/arweave-<date>/` unless you give another folder. Keep the links file private.

---

## 📊 Logs

Every minute the dashboard is running, it adds one line to `~/deck-logs/deck-log-YYYY-MM-DD.csv`:
time, CPU, temperature, RAM, battery, AC power, fan, network, internet, disks, and which servers are up.
One file per day; it opens in any spreadsheet app.
```
ls ~/deck-logs                       # list the log files
wc -l ~/deck-logs/*.csv              # how many readings (lowercase L)
tail -n 3 ~/deck-logs/*.csv          # the latest readings
```

---

## 🔄 Getting updates from this repository

First time only:
```
sudo apt install -y git
git clone https://github.com/<username>/elcaciquedeck.git
```
Every update after that:
```
cd ~/elcaciquedeck
git pull
```

---

## 🧭 Finding the laptop's address (for TV, phone, other PCs)

```
ip route get 1.1.1.1
```
The number after **`src`** is the address. Or use the menus: **Settings → Network → ⚙️ Wired → IPv4 Address**.

- `localhost` only works **on the laptop itself**.
- Every other device needs the **number**, for example `http://192.168.x.x:8096`.
- Phones and PCs may also accept `http://elcaciquedeck-00.local:8096`. Most smart TVs don't.

---

## ⚙️ One-time setup (already done, kept here for reference)

**Firewall: open the server ports**
```
sudo ufw allow 8080/tcp
sudo ufw allow 8096/tcp
sudo ufw allow 8888/tcp
```

**Laptop stays on with the lid closed.** Create the file with nano:
```
sudo mkdir -p /etc/systemd/logind.conf.d
sudo nano /etc/systemd/logind.conf.d/lid.conf
```
Type these lines, then save with **Ctrl+O**, **Enter**, **Ctrl+X**:
```
[Login]
HandleLidSwitch=ignore
HandleLidSwitchExternalPower=ignore
HandleLidSwitchDocked=ignore
```
**Never sleep**
```
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
```
Restart once. To undo the lid setting, delete `lid.conf` and restart.

**Computer name**
```
sudo hostnamectl set-hostname elcaciquedeck-00
```

---

## 🛠️ Quick fixes (lessons learned the hard way)

| Problem | Cause | Fix |
|---|---|---|
| `Unable to instantiate the HTTP Daemon` | The old server is still running on that port | `pkill kiwix-serve`, then start again |
| Kiwix prints a long help text (Usage / Purpose…) | A typo in the command | Check: two dashes in `--port`, spaces only after `kiwix-serve`, `--port`, `8080`; capital **L** in `Library` |
| `Unable to add the ZIM file … (1).zim` | Duplicate or unfinished download | Delete the `(1)` copy or the smaller file, then download again |
| New ZIM files don't show up | Kiwix only reads files when it starts | Ctrl+C, press **↑**, then **Enter** |
| Can't copy files bigger than 4 GB | Drive is FAT32 | Save the files elsewhere, reformat as **ext4** in the Disks app, copy them back |
| Drive not found after restart | External drives connect after login | Log in, click the drive in the Files app |
| `No such file or directory` | Wrong path or drive name | `ls /media/$USER/` to see the exact name |
| Page doesn't load on TV or phone | Using `localhost`, or a mistyped number | Use the laptop's number from `ip route get 1.1.1.1` |
| A long command fails when typed by hand | It was split across lines | One code box = **one** command, even if it wraps on screen |
| `systemctl` doesn't work | Typed with the number 1 | It's a lowercase **L**: system-c-t-**l** |
| `setfacl … Invalid argument` | Jellyfin came from the app store | Skip it. Store versions handle permissions differently |
| Force-close Firefox | Firefox frozen | `pkill -9 firefox` |
| The prompt shows `>` instead of your name | Bash is waiting for the rest of the command (for example a missing `done`) | Finish the command, or **Ctrl+C** to cancel |
| `wc: invalid option -- 1` | Number one instead of a lowercase L | `wc -l` |
| `snap "jellyfin" not found` | This deck's Jellyfin is the Flatpak version | `flatpak run org.jellyfin.JellyfinServer` |
| Docker: `permission denied … docker API` | User not in the docker group yet | `sudo usermod -aG docker $USER`, then reboot |
| `caciqueflix.home` doesn't open on a phone or TV | That device isn't using CaciqueGuard for DNS, or the server isn't running | Use the number address, or set the device's DNS to the laptop number |
| A `.home` name opens a search page instead | The browser treated it as a search | Type `http://` in front the first time, then bookmark it |
| AdGuard setup: "port 53 in use" | Ubuntu's DNS helper holds it | Run `setup-adguard.sh` again, it frees the port |
| A setup script shows `[FAIL]` | The line says what's wrong | Fix that one thing and run the same script again (they're safe to repeat) |
| Front page buttons point to an old number | The laptop's number changed | `bash ~/elcaciquedeck/homepage/setup-homepage.sh` |
| `caciquehome.home` shows "400: Bad Request" | Home Assistant doesn't trust the name helper yet | Run `homeassistant/setup-homeassistant.sh` again |
| Paperless says wrong user or password | Typo when created, or the username has different capitals | `docker compose exec webserver python3 manage.py changepassword USERNAME` |

---

## 📝 Useful commands

| Command | What it does |
|---|---|
| `ls` | List files in a folder |
| `cd folder` | Go into a folder (`cd ~` = home) |
| `mkdir name` | Create a folder |
| `mv source destination` | Move or rename |
| `df -h` | How much disk space is left |
| `lsblk -f` | List drives and their formats |
| `hostname -I` | Show the laptop's addresses |
| `sudo apt update && sudo apt full-upgrade -y` | Update everything |
| `sudo reboot` | Restart |

---

*Hecho en Puerto Rico 🇵🇷: one baby step at a time.*
