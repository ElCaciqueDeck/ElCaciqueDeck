#!/usr/bin/env bash
# ElCaciqueDeck - create everyone's accounts in every Cacique app
#
#   bash ~/elcaciquedeck/accounts/create-accounts.sh
#
# Before:  add the adults to the list (once):
#          bash ~/elcaciquedeck/accounts/people.sh add <login> <nickname>
# It asks for the admin login you use today in each app (press Enter to skip an app).
# After the first run, El Cacique is admin everywhere, so later runs don't need to ask.
# Safe to run again: it only adds what's missing; it never deletes or resets anything.
#
#   1. Checks the servers are running
#   2. Lets Familia and Invitado play the Arcade without a login (RomM "kiosk" mode)
#   3. Creates the accounts (CaciqueFlix, CaciquePhotos, CaciqueDocs, CaciqueArcade, CaciqueHome)
#      and invites the adults to CaciqueVault
#   4. Puts the "Familia Abierta" photo slideshow on the front page
#   5. Saves a card for each adult + El Cacique's logins for CaciqueVault (only on this laptop)

# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
ACC="$DATA/accounts"
start_report "accounts"
# the report must never contain passwords: the Python part prints none, and its prompts hide what you type

step "1/5  People and servers"
bash "$REPO/accounts/people.sh" list
grep -q '|adult$' "$ACC/people.txt" 2>/dev/null || warn "No adults on the list yet (people.sh add <login> <nickname>)"
for p in 8096:CaciqueFlix 2283:CaciquePhotos 8000:CaciqueDocs 8090:CaciqueArcade 8123:CaciqueHome 8222:CaciqueVault; do
    port="${p%%:*}"; name="${p#*:}"
    if [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 4 "http://127.0.0.1:$port/")" = "000" ]; then
        warn "$name is not running - it will be skipped (start-all.sh first, then run this again)"
    else
        ok "$name is running"
    fi
done

step "2/5  CaciqueArcade: play without a login for Familia and Invitado"
if [ -f "$REPO/arcade/.env" ]; then
    if grep -q '^KIOSK_MODE=true' "$REPO/arcade/.env"; then
        ok "Kiosk mode already on"
    else
        sed -i '/^KIOSK_MODE=/d' "$REPO/arcade/.env"
        echo "KIOSK_MODE=true" >> "$REPO/arcade/.env"
        (cd "$REPO/arcade" && docker compose up -d >"$REPORT_DIR/run-arcade-kiosk.log" 2>&1) \
            && ok "Kiosk mode on (visitors can browse and play, not change anything)" \
            || warn "Could not restart CaciqueArcade - see $REPORT_DIR/run-arcade-kiosk.log"
        wait_for "http://127.0.0.1:8090" 90 || warn "CaciqueArcade is slow to come back"
    fi
else
    info "CaciqueArcade isn't set up on this laptop"
fi

step "3/5  Creating the accounts"
python3 "$REPO/accounts/create_accounts.py" "$@"
RESULT=$?

step "4/5  Familia Abierta on the front page"
if [ -f "$ACC/open-photos-link.txt" ] && [ -f "$REPO/homepage/.env" ]; then
    LINK="$(cat "$ACC/open-photos-link.txt")"
    sed -i '/^HOMEPAGE_VAR_OPENPHOTOS=/d' "$REPO/homepage/.env"
    echo "HOMEPAGE_VAR_OPENPHOTOS=$LINK" >> "$REPO/homepage/.env"
    (cd "$REPO/homepage" && docker compose up -d --force-recreate >/dev/null 2>&1) \
        && ok "Front page button \"Familia Abierta\" opens the slideshow" || warn "Could not refresh the front page"
else
    info "No slideshow link yet (CaciquePhotos step skipped?)"
fi

step "5/5  What to do next"
[ "$RESULT" = "0" ] && ok "All accounts done" || warn "Some steps had problems - see the lines with FAILED above"
finish
cat <<EOT

 1. Give each adult their card (print it or read it to them):
      ls $ACC/cards/
      cat $ACC/cards/<login>.txt
 2. Log in to CaciqueVault as El Cacique (https://$(laptop_ip):8443, email elcacique@cacique.home,
    make its master password and write it on paper kept safe at home), then
    Tools -> Import data -> "Bitwarden (csv)" -> file:  $ACC/for-vaultwarden-import.csv
 3. When everyone has saved their passwords in CaciqueVault, delete the starter files:
      bash ~/elcaciquedeck/accounts/people.sh forget-passwords

EOT
