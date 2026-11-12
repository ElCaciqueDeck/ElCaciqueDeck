#!/usr/bin/env bash
# ElCaciqueDeck - Cacique Diario setup (the home's message of the day)
#   bash ~/elcaciquedeck/diario/setup-diario.sh
# Run again any time (safe): it keeps the password, the people, the reminders and every approval.
#
#   1. Checks Python and installs python3-pil (draws the picture cards for the frames and the TV)
#   2. Settings: makes the adults' password (saved only on this computer)
#   3. Firewall: opens port 8097 for the screens at home
#   4. Starts Cacique Diario and makes today's messages
# Nothing starts by itself at power-on: start-all.sh starts it (also in light mode, it's tiny).
# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
DIR="$REPO/diario"
ACC="$DATA/accounts"
start_report "diario-setup"

step "1/4  Checks"
command -v python3 >/dev/null && ok "Python 3 is here" || fail "Python 3 is missing (it comes with Ubuntu)."
if python3 -c "import PIL" 2>/dev/null; then
    ok "Picture cards: python3-pil is installed"
else
    sudo apt-get install -y python3-pil >/dev/null 2>&1 && ok "Picture cards: python3-pil installed" \
        || warn "Could not install python3-pil (no internet?). Messages work; picture cards start once it's installed."
fi
if python3 -c "import cryptography" 2>/dev/null; then
    ok "Encryption: python3-cryptography is installed"
else
    sudo apt-get install -y python3-cryptography >/dev/null 2>&1 && ok "Encryption: python3-cryptography installed" \
        || warn "Could not install python3-cryptography: the device recorder stays OFF (it never writes unencrypted)"
fi
IP="$(laptop_ip)"
[ -n "$IP" ] && ok "Server number: $IP" || warn "No house address right now (Wi-Fi/cable off?)"

step "2/4  Settings"
mkdir -p "$ACC" "$DATA/diario" && chmod 700 "$ACC"
PW=""
[ -f "$DIR/.env" ] && PW="$(grep -E '^DIARIO_PASSWORD=' "$DIR/.env" | cut -d= -f2-)"
[ -n "$PW" ] || PW="$(random_password | head -c 12)"
cat > "$DIR/.env" <<ENV
# Cacique Diario settings - written by setup-diario.sh, stays on this computer (never on GitHub)
DIARIO_PASSWORD=$PW
ENV
chmod 600 "$DIR/.env"
printf '%s\n' "$PW" > "$ACC/diario-password.txt"; chmod 600 "$ACC/diario-password.txt"
ok "Adults' password saved (only on this computer): ${ACC/#$HOME/~}/diario-password.txt"
chmod 700 "$DATA/diario" 2>/dev/null
if python3 -c "import cryptography" 2>/dev/null; then
    python3 -c "import sys; sys.path.insert(0, '$DIR'); import caciquediario as c; c.vault()" \
        && ok "Encryption key ready (only on this computer): ~/elcaciquedeck-data/keys/diario.key" \
        || warn "Could not make the encryption key"
fi

step "3/4  Firewall"
open_port 8097 "Cacique Diario"
ok "Screens at home can open port 8097"

step "4/4  Starting Cacique Diario"
mkdir -p "$REPO/reports/run"
pkill -f "[c]aciquediario.py" 2>/dev/null; sleep 1
nohup python3 "$DIR/caciquediario.py" >"$REPO/reports/run/diario.log" 2>&1 &
wait_for "http://127.0.0.1:8097/health" 30 && ok "Cacique Diario is running" || fail "It did not start - see reports/run/diario.log"
python3 "$DIR/caciquediario.py" --probar
if [ -f "$REPO/homepage/.env" ]; then
    mkdir -p "$REPO/homepage/icons" && cp -f "$REPO/homepage/custom-icons/diario.svg" "$REPO/homepage/icons/" 2>/dev/null
    bash "$REPO/homepage/make-live-config.sh" >/dev/null
    (cd "$REPO/homepage" && docker compose restart >/dev/null 2>&1) && ok "Front page button added (Hogar · Home)" \
        || warn "Front page button added; it shows after: bash ~/elcaciquedeck/start-all.sh --light"
fi
echo
echo "  SHARED SCREEN (TV, kitchen, tablet):  http://${IP:-<server>}:8097"
echo "  SMART MIRROR:                         http://${IP:-<server>}:8097/?modo=espejo"
echo "  ADULTS' PAGE (approve, people):       http://${IP:-<server>}:8097/admin"
echo "  DEVICE RECORDER: always on, encrypted, stays on this computer (Equipos y rutinas on the adults' page)."
echo "  Back up the key for the safe (paper or USB, never online):  cat ~/elcaciquedeck-data/keys/diario.key"
echo "  Next: open the adults' page, approve the Bible verses, add each person, and paste the"
echo "  CaciquePhotos key in Ajustes so the picture cards go to the \"Cacique Diario\" album."
finish
