#!/usr/bin/env bash
# ElCaciqueDeck - CaciqueHome (Home Assistant) setup
#
# Run once:   bash ~/elcaciquedeck/homeassistant/setup-homeassistant.sh
#
#   1. Checks Docker
#   2. Creates the settings folder on the laptop's own disk
#   3. Opens the firewall for port 8123
#   4. Downloads and starts Home Assistant
#   5. Lets the http://caciquehome.home name work (trusts the local name helper)
#   6. Tests it and saves a report
#
# Safe to run again.

# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
DIR="$REPO/homeassistant"
CONF="$DATA/homeassistant"
start_report "homeassistant-setup"

step "1/6  Checks"
need_docker
IP="$(laptop_ip)"; [ -n "$IP" ] && ok "Laptop number: $IP" || warn "Could not find the laptop number"

step "2/6  Settings folder"
mkdir -p "$CONF" && ok "Settings stored in: $CONF" || fail "Could not create $CONF"
if [ ! -f "$DIR/.env" ]; then
    printf '# CaciqueHome private settings - stays on this laptop\nHA_CONFIG=%s\n' "$CONF" > "$DIR/.env"
    ok "Created .env"
else
    ok ".env already exists"
fi

step "3/6  Firewall"
open_port 8123 "CaciqueHome"

step "4/6  Downloading and starting (first time: a few minutes, about 1.5 GB)"
cd "$DIR" || fail "Can't open $DIR"
docker compose pull || fail "Download failed. Check the internet and run this again."
docker compose up -d || fail "Could not start Home Assistant."
ok "Container started"

step "5/6  Allow the caciquehome.home name"
# Home Assistant creates configuration.yaml on its first start; wait for it.
for _ in $(seq 1 40); do
    [ -f "$CONF/configuration.yaml" ] && break
    sleep 3
done
if [ ! -f "$CONF/configuration.yaml" ]; then
    warn "configuration.yaml not created yet - run this script again in a minute"
elif sudo grep -q "use_x_forwarded_for" "$CONF/configuration.yaml"; then
    ok "Name helper already trusted"
else
    printf '\n# ElCaciqueDeck: allow http://caciquehome.home (Caddy on this same laptop)\nhttp:\n  use_x_forwarded_for: true\n  trusted_proxies:\n    - 127.0.0.1\n    - ::1\n' \
        | sudo tee -a "$CONF/configuration.yaml" >/dev/null
    docker compose restart >/dev/null && ok "Name helper trusted, CaciqueHome restarted"
fi

step "6/6  Testing (Home Assistant takes 1-3 minutes to wake up the first time)"
if wait_for "http://127.0.0.1:8123" 240; then
    ok "CaciqueHome answers on port 8123"
else
    warn "Not answering yet. Check in a minute with: docker compose logs homeassistant"
fi

finish
cat <<EOT

 NEXT (one time only):
  1. Open  http://${IP:-<laptop number>}:8123   and click "Create my smart home"
  2. Create your account, set the home location (Puerto Rico), units, etc.
  3. On the last screen it lists devices it found by itself.
     Philips Hue: click it, then PRESS THE BIG BUTTON on top of the Hue Bridge,
     then click Submit. Your lights appear and work without internet.

EOT
