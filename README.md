# 🇵🇷 ElCaciqueDeck: a Puerto Rican home lab

> **⚠️ For learning purposes only.**
> This is a home-based Puerto Rican project: a home lab built step by step by a **total beginner**.
> Everything here is shared as a learning journal. Use it at your own risk, adapt it to your own setup,
> and always understand a command before you run it.

---

## What this is

ElCaciqueDeck is an old Intel ThinkPad running **Ubuntu Linux**. It's being turned into a small,
self-reliant home server that works **without the internet**:

| Server | What it does | Address |
|---|---|---|
| 📚 **Kiwix** | Offline encyclopedia: Wikipedia, wikiHow, iFixit, dictionaries, books (English and Spanish) | `http://<laptop number>:8080` |
| 🎬 **Jellyfin** | Home movie and series server for media the family owns | `http://<laptop number>:8096` |
| 🏎️ **Dashboard** | JDM-style gauges: CPU, RAM, temperature, battery, fan, network, disks | `http://<laptop number>:8888` |

Also on the deck: offline maps of Puerto Rico (Organic Maps) and Meshtastic (LoRa mesh radio, in progress).

**Road ahead:** RTL-SDR radio listening, Meshtastic node, and a 3-node mini-PC Proxmox cluster in a 10" rack.

---

## 📁 Drive layout

```
Library (external drive)
├── Kiwix/                     ← all .zim files
└── MEDIA/Jellyfin/
    ├── Movies/   Coco (2017)/Coco (2017).mkv
    ├── Series/   Show Name (2005)/Season 01/Show Name S01E01.mkv
    └── Anime/    Show Name (2005)/Season 01/Show Name S01E01.mkv
```

---

## ▶️ Starting the 3 servers

Each server runs in its **own Terminal window**. Open a new one with **Ctrl+Alt+T**.
Stop any of them with **Ctrl+C** in its window.

**1. Kiwix (library)**
```
kiwix-serve --port 8080 /media/$USER/Library/Kiwix/*.zim
```

**2. Jellyfin (movies).** The command depends on how it was installed:
```
sudo snap start jellyfin        # snap version
sudo snap stop jellyfin
```
```
sudo systemctl start jellyfin   # official installer version
sudo systemctl stop jellyfin
```

**3. Dashboard**
```
cd ~/elcaciquedeck
python3 caciquedash.py
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
