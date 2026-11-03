#!/usr/bin/env bash
# ElCaciqueDeck - CaciqueFinanzas setup (family budget + AI money coach)
#   bash ~/elcaciquedeck/finanzas/setup-finanzas.sh
# Run again any time (safe): it keeps the budgets, the password and the coach's rules.
#
#   1. Checks Docker, the Vault drive and CaciqueGuard (Caddy makes the secure doors)
#   2. Settings: makes the family budget password (saved only on this laptop)
#   3. Firewall for the two secure doors (5443 budget, 5444 coach)
#   4. Starts Actual Budget and sets its password
#   5. Starts the reading helper, reloads Caddy, starts the coach page
# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
DIR="$REPO/finanzas"
ACC="$DATA/accounts"
start_report "finanzas-setup"

step "1/5  Checks"
need_docker
need_vault
IP="$(laptop_ip)"
[ -n "$IP" ] && ok "Laptop number: $IP" || fail "Could not find the laptop number (is the network on?)"
[ -d "$REPO/adguard/conf" ] || docker ps -a --format '{{.Names}}' | grep -qx caciquenames \
    || fail "CaciqueGuard (Caddy) isn't set up yet. Run adguard/setup-adguard.sh first."

step "2/5  Settings"
mkdir -p "$ACC" && chmod 700 "$ACC"
FDIR="$VAULT/finanzas"
mkdir -p "$FDIR/server" "$FDIR/api-cache" "$DATA/finanzas" || fail "Could not make $FDIR"
PW=""; KEY=""
if [ -f "$DIR/.env" ]; then
    PW="$(grep -E '^FINANZAS_PASSWORD=' "$DIR/.env" | cut -d= -f2-)"
    KEY="$(grep -E '^FINANZAS_API_KEY=' "$DIR/.env" | cut -d= -f2-)"
fi
[ -n "$PW" ] || PW="$(random_password | head -c 12)"
[ -n "$KEY" ] || KEY="$(random_password)"
cat > "$DIR/.env" <<ENV
# CaciqueFinanzas settings - written by setup-finanzas.sh, stays on this laptop (never on GitHub)
FINANZAS_DIR=$FDIR
FINANZAS_PASSWORD=$PW
FINANZAS_API_KEY=$KEY
ENV
chmod 600 "$DIR/.env"
printf '%s\n' "$PW" > "$ACC/finanzas-password.txt"; chmod 600 "$ACC/finanzas-password.txt"
ok "Budgets stored on the Vault drive: $FDIR"
ok "Family budget password saved (only on this laptop): $ACC/finanzas-password.txt"
grep -q '^CACIQUE_IP=' "$REPO/adguard/.env" 2>/dev/null || printf 'CACIQUE_IP=%s\n' "$IP" > "$REPO/adguard/.env"

step "3/5  Firewall"
open_port 5443 "CaciqueFinanzas"
open_port 5444 "CaciqueFinanzas coach"

step "4/5  Downloading and starting Actual Budget"
cd "$DIR" || fail "Can't open $DIR"
docker compose pull || fail "Download failed. Check the internet and run this again."
docker compose up -d actual || fail "Could not start Actual Budget."
wait_for "http://127.0.0.1:5006/account/needs-bootstrap" 90 || fail "Actual Budget did not answer"
if curl -s http://127.0.0.1:5006/account/needs-bootstrap | grep -q '"bootstrapped":false'; then
    R="$(curl -s -X POST -H 'Content-Type: application/json' \
         -d "{\"password\":\"$PW\"}" http://127.0.0.1:5006/account/bootstrap)"
    echo "$R" | grep -q '"status":"ok"' && ok "Budget password set" || fail "Could not set the budget password: $R"
else
    ok "Budget password was already set (kept)"
fi

step "5/5  Reading helper, secure doors and coach"
docker compose up -d api || fail "Could not start the reading helper."
wait_for "http://127.0.0.1:5007/v1/actualhttpapiversion" 60 && ok "Reading helper running" || warn "Reading helper not answering yet"
(cd "$REPO/adguard" && docker compose up -d --force-recreate caddy >"$REPORT_DIR/run-caddy-finanzas.log" 2>&1) \
    && ok "Caddy reloaded (secure doors 5443 and 5444)" || fail "Caddy reload failed - see $REPORT_DIR/run-caddy-finanzas.log"
mkdir -p "$REPO/reports/run"; pkill -f "[c]aciquefinanzas.py" 2>/dev/null
nohup python3 "$DIR/caciquefinanzas.py" >"$REPO/reports/run/finanzas.log" 2>&1 &
sleep 3
wait_for "http://127.0.0.1:8075/health" 20 && ok "Coach page running" || warn "Coach page not answering yet (see reports/run/finanzas.log)"
echo
echo "  Budget app:  https://$IP:5443   (first time: open it, type the budget password, 'Start fresh')"
echo "  Coach:       https://$IP:5444   (same password)"
echo "  Password:    in $ACC/finanzas-password.txt  - keep a copy in CaciqueVault"
echo "  Phones need the Cacique certificate once:  http://$IP/cacique-ca.crt"
finish
