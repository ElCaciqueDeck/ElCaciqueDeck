#!/usr/bin/env bash
# ElCaciqueDeck - CaciqueArcade (RomM) setup
#
# Run once:   bash ~/elcaciquedeck/arcade/setup-arcade.sh
#
#   1. Checks Docker and the Library drive
#   2. Creates the game folders on the Library drive (one per console)
#   3. Writes the private settings file (.env) with random passwords
#   4. Adds a first free game: µCity (Game Boy Color, open source, GPLv3)
#   5. Downloads and starts RomM, tests it, and saves a report
#
# Safe to run again: it never replaces passwords or deletes games.

# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
DIR="$REPO/arcade"
ARCADE="$LIBRARY/Arcade"
start_report "arcade-setup"

step "1/5  Checks"
need_docker
need_library
IP="$(laptop_ip)"; [ -n "$IP" ] && ok "Laptop number: $IP" || warn "Could not find the laptop number"

step "2/5  Game folders on the Library drive"
# Folder names are the ones RomM recognizes. Add more any time (e.g. nds, ps2, ngc, wii).
for p in gb gbc gba nes snes genesis sms gamegear n64 psx arcade; do
    mkdir -p "$ARCADE/library/roms/$p"
done
mkdir -p "$ARCADE/library/bios" "$ARCADE/assets" "$ARCADE/config" "$ARCADE/LICENSES"
ok "Games go in: $ARCADE/library/roms/<console>/"
info "Consoles ready: gb gbc gba nes snes genesis sms gamegear n64 psx arcade"

step "3/5  Private settings (.env)"
if [ -f "$DIR/.env" ]; then
    ok ".env already exists - keeping your passwords"
else
    cat > "$DIR/.env" <<ENV
# CaciqueArcade private settings - stays on this laptop, never uploaded
ARCADE_PATH=$ARCADE
DB_PASSWD=$(random_password)
DB_ROOT_PASSWD=$(random_password)
ROMM_AUTH_SECRET_KEY=$(openssl rand -hex 32)
ENV
    chmod 600 "$DIR/.env"
    ok "Created .env with random passwords"
fi

step "4/5  First free game: µCity (Game Boy Color city builder, GPLv3)"
GAME="$ARCADE/library/roms/gbc/uCity.gbc"
if [ -s "$GAME" ]; then
    ok "µCity already in the arcade"
elif curl -sfL --max-time 60 -o "$GAME" "https://github.com/AntonioND/ucity/releases/download/v1.3/ucity.gbc"; then
    printf 'µCity by Antonio Niño Díaz - free, open-source Game Boy Color game.\nLicense: GNU GPL v3.  Source code: https://github.com/AntonioND/ucity\n' \
        > "$ARCADE/LICENSES/uCity.txt"
    ok "µCity added (official release from its author)"
else
    rm -f "$GAME"; warn "Could not download µCity (needs internet once) - the arcade still works"
fi

step "5/5  Downloading and starting (first time: a few minutes)"
cd "$DIR" || fail "Can't open $DIR"
docker compose pull || fail "Download failed. Check the internet and run this again."
docker compose up -d || fail "Could not start CaciqueArcade."
ok "Containers started"
if wait_for "http://127.0.0.1:8090" 180; then
    ok "CaciqueArcade answers on port 8090"
else
    warn "Not answering yet. Check in a minute with: docker compose logs romm"
fi

if grep -q '# >>> elcaciquedeck names >>>' /etc/hosts && ! grep -q 'caciquearcade.home' /etc/hosts; then
    sudo sed -i '/# >>> elcaciquedeck names >>>/{n;s/$/ caciquearcade.home/}' /etc/hosts && ok "Added caciquearcade.home to this laptop's names"
fi

finish
cat <<EOT

 NEXT (one time only):
  1. Open  http://${IP:-<laptop number>}:8090  and create the admin account
  2. Click the menu -> Scan -> "Scan" to find the games on the Library drive
  3. Open µCity -> press Play. It runs right in the browser.

 THEN refresh the front page so it shows the Arcade button:
    bash ~/elcaciquedeck/homepage/setup-homepage.sh

 ADD YOUR OWN GAMES: copy them into  $ARCADE/library/roms/<console>/
 (for example roms/snes/ for Super Nintendo), then Scan again.

EOT
