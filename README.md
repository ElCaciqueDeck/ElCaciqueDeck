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
| 🧭 **Cacique** | Caddy | Front page with a button for every server | `http://cacique.home` | — |
| 📚 **CaciqueLibrary** | Kiwix | Offline encyclopedia: Wikipedia, wikiHow, iFixit, dictionaries, books (English and Spanish) | `http://caciquelibrary.home` | `:8080` |
| 🎬 **CaciqueFlix** | Jellyfin | Movies, series and anime the family owns | `http://caciqueflix.home` | `:8096` |
| 📄 **CaciqueDocs** | Paperless-ngx | Private document vault: scan, OCR (Spanish and English), tag and search | `http://caciquedocs.home` | `:8000` |
| 🏎️ **CaciqueDash** | caciquedash.py | JDM-style gauges, plus a log reading every minute | `http://caciquedash.home` | `:8888` |
| 🛡️ **CaciqueGuard** | AdGuard Home | Gives every server its easy name, blocks ads for devices that use it | `http://caciqueguard.home` | `:3000` |

"Number address" = `http://<laptop number>:<port>`. It always works, even when the easy names don't.

Also on the deck: offline maps of Puerto Rico (Organic Maps) and Meshtastic (LoRa mesh radio, in progress).

**Single-laptop roadmap:** ✅ Docker → ✅ CaciqueDocs (Paperless-ngx) → 🔧 CaciqueGuard (AdGuard Home) → CaciquePhotos (Immich) → CaciqueHome (Home Assistant) → Cacique (Homepage)

**Road ahead:** RTL-SDR radio listening, Meshtastic node, and a 3-node mini-PC Proxmox cluster in a 10" rack.

---

## 📁 Drive layout

```
Library (external drive)
├── Kiwix/                     ← all .zim files
├── Vault/paperless/           ← document vault (data, media, export, consume)
└── MEDIA/Jellyfin/
    ├── Movies/   Coco (2017)/Coco (2017).mkv
    ├── Series/   Show Name (2005)/Season 01/Show Name S01E01.mkv
    └── Anime/    Show Name (2005)/Season 01/Show Name S01E01.mkv
```

---

## ▶️ Starting the servers

Each server runs in its **own Terminal window**. Open a new one with **Ctrl+Alt+T**.
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
