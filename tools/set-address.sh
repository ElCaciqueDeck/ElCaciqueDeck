#!/usr/bin/env bash
# ElCaciqueDeck - give the server a FIXED address and update El Cacique to use it (one command)
#
#   bash ~/elcaciquedeck/tools/set-address.sh                 fixed address 192.168.x.27 (same network, number 27)
#   bash ~/elcaciquedeck/tools/set-address.sh 192.168.40.50   fixed address of your choice
#   bash ~/elcaciquedeck/tools/set-address.sh --check         only SHOW what it would do (changes nothing)
#   bash ~/elcaciquedeck/tools/set-address.sh --auto          undo: back to an automatic address from the router
#
# Use it when the router can't reserve an address (some Liberty/Sagemcom routers hide that option).
#   1. Finds the connection in use (Wi-Fi or cable), the current address and the router
#   2. Checks the new number is free (nobody answers on it)
#   3. Sets the fixed address on this computer (the router keeps doing everything else)
#   4. Replaces the old address in El Cacique's settings: front page buttons, the secure doors (Caddy),
#      CaciqueVault, the .home names (AdGuard), the Familia Abierta link and the account cards
#   5. Restarts what uses the address and tests the front page
# Safe to run again. Nothing is deleted; every settings file it changes gets a .bak copy first.
# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
start_report "set-address"
CHECK=0; AUTO=0; WANT=""
for a in "$@"; do
    case "$a" in --check) CHECK=1 ;; --auto) AUTO=1 ;; *) WANT="$a" ;; esac
done
do_() { if [ "$CHECK" = 1 ]; then echo "  would run: $*"; else "$@"; fi; }

step "1/5  The connection in use"
DEV="$(ip route show default 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev"){print $(i+1); exit}}')"
GW="$(ip route show default 2>/dev/null | awk '{print $3; exit}')"
[ -n "$DEV" ] && [ -n "$GW" ] || fail "No network connection found. Connect to the home Wi-Fi (or cable) and run this again."
CON="$(nmcli -t -f NAME,DEVICE connection show --active | awk -F: -v d="$DEV" '$2==d{print $1; exit}')"
[ -n "$CON" ] || fail "Could not find the NetworkManager connection for $DEV"
CUR="$(ip -4 -o addr show dev "$DEV" | awk '{print $4; exit}')"      # e.g. 192.168.40.33/24
CUR_IP="${CUR%/*}"; PREFIX="${CUR#*/}"
ok "Connection: \"$CON\" on $DEV ($( [[ $DEV == wl* ]] && echo Wi-Fi || echo cable ))"
ok "Address now: $CUR_IP   Router: $GW"

if [ "$AUTO" = 1 ]; then
    step "Back to an automatic address"
    do_ nmcli connection modify "$CON" ipv4.method auto ipv4.addresses "" ipv4.gateway "" ipv4.dns ""
    do_ nmcli connection up "$CON"
    ok "Automatic address again. If the number changes, run this tool once more with the number you want."
    finish; exit 0
fi

[ -n "$WANT" ] || WANT="${GW%.*}.27"
[[ "$WANT" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail "\"$WANT\" is not an address like 192.168.40.27"
[ "${WANT%.*}" = "${GW%.*}" ] || fail "$WANT is not on the same network as the router ($GW). Use ${GW%.*}.<number>"
[ "$WANT" != "$GW" ] || fail "That's the router's own address. Pick another number."

step "2/5  Is $WANT free?"
if [ "$WANT" = "$CUR_IP" ]; then
    ok "This computer already has $WANT (it will be made permanent)"
elif ping -c 2 -W 1 "$WANT" >/dev/null 2>&1; then
    fail "Another device answers on $WANT. Choose another number, e.g.: bash ~/elcaciquedeck/tools/set-address.sh ${GW%.*}.50"
else
    ok "Nobody answers on $WANT - it's free"
fi

# every old address El Cacique may have saved (the current one + the one the front page was set up with)
OLD="$(grep -h '^HOMEPAGE_VAR_IP=' "$REPO/homepage/.env" 2>/dev/null | cut -d= -f2)"
OLDS="$(printf '%s\n%s\n' "$CUR_IP" "$OLD" | grep -v "^$WANT$" | grep -E '^[0-9.]+$' | sort -u)"

if [ "$CHECK" = 0 ]; then
    echo
    echo "  This computer will keep the address $WANT (router $GW)."
    [ -n "$OLDS" ] && echo "  El Cacique settings will change from: $(echo $OLDS) -> $WANT"
    read -r -p "  Continue? Type yes: " A; [ "$A" = "yes" ] || fail "Nothing changed."
    sudo -v || fail "This needs your password."
fi

step "3/5  Fixed address"
do_ nmcli connection modify "$CON" ipv4.method manual ipv4.addresses "$WANT/${PREFIX:-24}" ipv4.gateway "$GW" ipv4.dns "$GW"
if [ "$CHECK" = 0 ]; then
    nmcli connection up "$CON" >/dev/null 2>&1 || { sleep 3; nmcli connection up "$CON" >/dev/null 2>&1; }
    sleep 4
    NOW="$(ip -4 -o addr show dev "$DEV" | awk '{print $4; exit}')"; NOW="${NOW%/*}"
    [ "$NOW" = "$WANT" ] && ok "Address is now $WANT (fixed)" || fail "The address is $NOW, not $WANT. Undo with: bash ~/elcaciquedeck/tools/set-address.sh --auto"
    ping -c 1 -W 2 "$GW" >/dev/null 2>&1 && ok "Router answers" || warn "The router doesn't answer yet"
fi

step "4/5  El Cacique settings"
FILES="$(ls "$REPO"/*/.env 2>/dev/null) $REPO/adguard/conf/AdGuardHome.yaml $DATA/accounts/open-photos-link.txt"
FILES="$FILES $(ls "$DATA"/accounts/cards/*.txt "$DATA"/accounts/for-vaultwarden-import.csv 2>/dev/null)"
changed=0
for f in $FILES; do
    [ -f "$f" ] || continue
    for o in $OLDS; do
        if sudo grep -qF "$o" "$f" 2>/dev/null; then
            if [ "$CHECK" = 1 ]; then echo "  would change $o -> $WANT in: $f"; continue; fi
            sudo cp -p "$f" "$f.bak" && sudo sed -i "s/$(printf '%s' "$o" | sed 's/\./\\./g')\([^0-9]\|$\)/$WANT\1/g" "$f" \
                && ok "updated: ${f/#$HOME/~}" && changed=1
        fi
    done
done
[ "$changed" = 1 ] || [ "$CHECK" = 1 ] || info "No saved settings had the old address"
[ -f "$REPO/office/.env" ] && warn "CaciqueOffice keeps its address inside Nextcloud too: run office/setup-office.sh again after this"

step "5/5  Restart and test"
if [ "$CHECK" = 1 ]; then
    echo "  would restart: CaciqueGuard + Caddy (adguard), CaciqueVault, CaciqueFinanzas, front page"
    echo; echo "  CHECK ONLY - nothing was changed. To do it:  bash ~/elcaciquedeck/tools/set-address.sh${WANT:+ $WANT}"
    finish; exit 0
fi
for d in adguard vaultwarden finanzas; do
    if [ -f "$REPO/$d/docker-compose.yml" ] && (cd "$REPO/$d" && docker compose ps -q 2>/dev/null | grep -q .); then
        (cd "$REPO/$d" && docker compose up -d --force-recreate >/dev/null 2>&1) && ok "restarted: $d" || warn "could not restart $d"
    fi
done
bash "$REPO/homepage/make-live-config.sh" >/dev/null
if [ -f "$REPO/homepage/.env" ]; then
    (cd "$REPO/homepage" && docker compose up -d --force-recreate >/dev/null 2>&1) && ok "restarted: front page" || warn "could not restart the front page"
fi
sleep 8
C="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 -H "Host: $WANT" http://127.0.0.1/)"
[ "$C" = "200" ] && ok "Front page answers at http://$WANT" || warn "Front page answered $C (give it a minute, then: bash ~/elcaciquedeck/status.sh)"
echo
echo "  FAMILY FRONT DOOR:  http://$WANT     (bookmarks and home-screen icons should use this)"
echo "  Phones that use CaciqueVault/Finanzas: open http://$WANT/cacique-ca.crt once more if they warn about the certificate."
finish
