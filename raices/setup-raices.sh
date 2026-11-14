#!/usr/bin/env bash
# ElCaciqueDeck - Cacique Raíces setup (the family's own encyclopedia: our roots, our story)
#   bash ~/elcaciquedeck/raices/setup-raices.sh
# Run again any time (safe): it keeps every page, photo, PIN and password.
#
#   1. Checks Python and python3-pil (resizes photos and removes their hidden location data)
#   2. Settings: where the pages live (the Vault drive when it's connected), the adults' password
#   3. Firewall: opens port 8098 for the devices at home
#   4. Starts Cacique Raíces and adds its button to the front page
# Nothing starts by itself at power-on: start-all.sh starts it (also in light mode, it's tiny).
# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
DIR="$REPO/raices"
ACC="$DATA/accounts"
start_report "raices-setup"

step "1/4  Checks"
command -v python3 >/dev/null && ok "Python 3 is here" || fail "Python 3 is missing (it comes with Ubuntu)."
if python3 -c "import PIL" 2>/dev/null; then
    ok "Photos: python3-pil is installed"
else
    sudo apt-get install -y python3-pil >/dev/null 2>&1 && ok "Photos: python3-pil installed" \
        || fail "Could not install python3-pil (needed for the photos). Check the internet and run this again."
fi
IP="$(laptop_ip)"
[ -n "$IP" ] && ok "Server number: $IP" || warn "No house address right now (Wi-Fi/cable off?)"

step "2/4  Settings"
mkdir -p "$ACC" && chmod 700 "$ACC"
PW=""; SEC=""; RDIR=""
if [ -f "$DIR/.env" ]; then
    PW="$(grep -E '^RAICES_PASSWORD=' "$DIR/.env" | cut -d= -f2-)"
    SEC="$(grep -E '^RAICES_SECRET=' "$DIR/.env" | cut -d= -f2-)"
    RDIR="$(grep -E '^RAICES_DIR=' "$DIR/.env" | cut -d= -f2-)"
fi
[ -n "$PW" ] || PW="$(random_password | head -c 12)"
[ -n "$SEC" ] || SEC="$(random_password)"
if [ -z "$RDIR" ]; then
    if drive_ready "$VAULT"; then RDIR="$VAULT/raices"; else RDIR="$DATA/raices"; fi
fi
mkdir -p "$RDIR" && chmod 700 "$RDIR" || fail "Could not make $RDIR"
cat > "$DIR/.env" <<ENV
# Cacique Raíces settings - written by setup-raices.sh, stays on this computer (never on GitHub)
RAICES_DIR=$RDIR
RAICES_PASSWORD=$PW
RAICES_SECRET=$SEC
ENV
chmod 600 "$DIR/.env"
printf '%s\n' "$PW" > "$ACC/raices-password.txt"; chmod 600 "$ACC/raices-password.txt"
ok "The family's pages and photos live in: $RDIR"
ok "Adults' password saved (only on this computer): ${ACC/#$HOME/~}/raices-password.txt"

step "3/4  Firewall"
open_port 8098 "Cacique Raíces"
ok "Devices at home can open port 8098"

step "4/4  Starting Cacique Raíces"
mkdir -p "$REPO/reports/run"
pkill -f "[c]aciqueraices.py" 2>/dev/null; sleep 1
nohup python3 "$DIR/caciqueraices.py" >"$REPO/reports/run/raices.log" 2>&1 &
wait_for "http://127.0.0.1:8098/health" 30 && ok "Cacique Raíces is running" || fail "It did not start - see reports/run/raices.log"
if [ -f "$REPO/homepage/.env" ]; then
    mkdir -p "$REPO/homepage/icons" && cp -f "$REPO/homepage/custom-icons/raices.svg" "$REPO/homepage/icons/" 2>/dev/null
    bash "$REPO/homepage/make-live-config.sh" >/dev/null
    (cd "$REPO/homepage" && docker compose restart >/dev/null 2>&1) && ok "Front page button added (Familia)" \
        || warn "Front page button added; it shows after: bash ~/elcaciquedeck/start-all.sh --light"
fi
echo
echo "  THE FAMILY'S PAGES:   http://${IP:-<server>}:8098"
echo "  ADULTS' PAGE:         http://${IP:-<server>}:8098/admin     (password: cat ~/elcaciquedeck-data/accounts/raices-password.txt)"
echo "  First: in the adults' page set the family name, motto and the FAMILY CODE, then add each person with a PIN."
finish
