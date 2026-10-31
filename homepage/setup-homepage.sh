#!/usr/bin/env bash
# ElCaciqueDeck - Cacique (Homepage) setup
#
# Run once:   bash ~/elcaciquedeck/homepage/setup-homepage.sh
# Run again any time the laptop's number (IP) changes - it updates the buttons.
#
#   1. Checks Docker
#   2. Writes .env with the laptop's number (fills in every button)
#   3. Saves the app icons on the laptop so the page works offline
#   4. Downloads and starts the Homepage
#   5. Refreshes the name helper (Caddy) so the plain address shows it
#   6. Tests it and saves a report

# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
DIR="$REPO/homepage"
start_report "homepage-setup"

step "1/6  Checks"
need_docker
IP="$(laptop_ip)"
[ -n "$IP" ] && ok "Laptop number: $IP" || fail "Could not find the laptop number (is the network cable in?)"

step "2/6  Settings (.env)"
cat > "$DIR/.env" <<ENV
# Cacique Homepage settings - written by setup-homepage.sh, stays on this laptop
HOMEPAGE_VAR_IP=$IP
HOMEPAGE_ALLOWED_HOSTS=$IP,$IP:80,$IP:3001,cacique.home,localhost,localhost:3001,127.0.0.1:3001
LIBRARY_PATH=$LIBRARY
PUID=$(id -u)
PGID=$(id -g)
ENV
ok "Buttons will point to $IP"

step "3/6  Saving icons on the laptop (for offline use)"
mkdir -p "$DIR/icons"
CDN="https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png"
for i in jellyfin immich kiwix romm paperless-ngx home-assistant adguard-home; do
    if [ -s "$DIR/icons/$i.png" ]; then
        ok "$i icon already saved"
    elif curl -sfL --max-time 20 -o "$DIR/icons/$i.png" "$CDN/$i.png"; then
        ok "$i icon saved"
    else
        rm -f "$DIR/icons/$i.png"; warn "Could not download the $i icon (needs internet once)"
    fi
done
if [ -s "$DIR/icons/speedometer.svg" ] || curl -sfL --max-time 20 -o "$DIR/icons/speedometer.svg" \
        "https://cdn.jsdelivr.net/npm/@mdi/svg/svg/speedometer.svg"; then
    ok "speedometer icon saved"
else
    rm -f "$DIR/icons/speedometer.svg"; warn "Could not download the speedometer icon"
fi

step "4/6  Downloading and starting the Homepage"
open_port 3001 "Homepage"
cd "$DIR" || fail "Can't open $DIR"
docker compose pull || fail "Download failed. Check the internet and run this again."
docker compose up -d --force-recreate || fail "Could not start the Homepage."
ok "Container started"

step "5/6  Refreshing the name helper (Caddy)"
if [ -d "$REPO/adguard/conf" ] || docker ps -a --format '{{.Names}}' | grep -qx caciquenames; then
    (cd "$REPO/adguard" && docker compose up -d --force-recreate caddy >/dev/null 2>&1) \
        && ok "Caddy reloaded with the new front page" || warn "Could not reload Caddy (run: cd ~/elcaciquedeck/adguard && docker compose up -d --force-recreate caddy)"
else
    warn "CaciqueGuard isn't set up yet, so the plain address won't show the Homepage. Run adguard/setup-adguard.sh first."
fi

step "6/6  Testing"
if wait_for "http://127.0.0.1:3001" 60; then ok "Homepage answers on port 3001"; else warn "Homepage not answering yet (give it a minute)"; fi
C="$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 -H "Host: $IP" http://127.0.0.1/)"
[ "$C" = "200" ] && ok "http://$IP shows the Homepage" || warn "http://$IP answered $C"

finish
cat <<EOT

 FAMILY FRONT DOOR:  http://$IP
   On each phone: open it once -> Share / menu -> "Add to Home Screen" -> name it Cacique

 If the laptop's number ever changes, run this script again to update every button.

EOT
