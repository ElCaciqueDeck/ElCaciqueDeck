#!/usr/bin/env bash
# ElCaciqueDeck - CaciqueVault setup (Vaultwarden password safe + secure https door)
#
# Run once:   bash ~/elcaciquedeck/vaultwarden/setup-vault.sh
# Run again any time (safe): it keeps the vaults and the admin key.
#
#   1. Checks Docker and the Vault drive (the passwords live there)
#   2. Writes the settings (.env) and makes the admin key (saved only on this laptop)
#   3. Opens the firewall for the secure door (8443) and the .home name (443)
#   4. Downloads and starts Vaultwarden
#   5. Reloads Caddy so it makes the "Cacique certificate" and opens https://<laptop number>:8443
#   6. Tests it and shows the next steps

# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
DIR="$REPO/vaultwarden"
ACC="$DATA/accounts"
start_report "vault-setup"

step "1/6  Checks"
need_docker
need_vault
IP="$(laptop_ip)"
[ -n "$IP" ] && ok "Laptop number: $IP" || fail "Could not find the laptop number (is the network cable in?)"
sudo -v || fail "This needs your password."

step "2/6  Settings"
mkdir -p "$ACC" && chmod 700 "$ACC"
VWDIR="$VAULT/vaultwarden"
mkdir -p "$VWDIR" || sudo mkdir -p "$VWDIR"
TOKEN=""
[ -f "$DIR/.env" ] && TOKEN="$(grep -E '^ADMIN_TOKEN=' "$DIR/.env" | cut -d= -f2-)"
[ -n "$TOKEN" ] || TOKEN="$(random_password)$(random_password)"
cat > "$DIR/.env" <<ENV
# CaciqueVault settings - written by setup-vault.sh, stays on this laptop (never on GitHub)
DOMAIN=https://$IP:8443
VAULTWARDEN_DIR=$VWDIR
ADMIN_TOKEN=$TOKEN
ENV
chmod 600 "$DIR/.env"
printf '%s\n' "$TOKEN" > "$ACC/vaultwarden-admin-token.txt"; chmod 600 "$ACC/vaultwarden-admin-token.txt"
ok "Vaults will be stored on the Vault drive: $VWDIR"
ok "Admin key saved (only on this laptop): $ACC/vaultwarden-admin-token.txt"
# Caddy needs the laptop number to make a certificate for it
printf 'CACIQUE_IP=%s\n' "$IP" > "$REPO/adguard/.env"
ok "Caddy will open https://$IP:8443"

step "3/6  Firewall"
open_port 8443 "CaciqueVault"
open_port 443 "CaciqueVault (.home name)"

step "4/6  Downloading and starting Vaultwarden"
cd "$DIR" || fail "Can't open $DIR"
docker compose pull || fail "Download failed. Check the internet and run this again."
docker compose up -d || fail "Could not start CaciqueVault."
ok "CaciqueVault started"

step "5/6  Secure door (Caddy + Cacique certificate)"
if [ -d "$REPO/adguard/conf" ] || docker ps -a --format '{{.Names}}' | grep -qx caciquenames; then
    (cd "$REPO/adguard" && docker compose up -d --force-recreate caddy >"$REPORT_DIR/run-caddy-vault.log" 2>&1) \
        && ok "Caddy reloaded" || fail "Caddy reload failed - see $REPORT_DIR/run-caddy-vault.log"
else
    fail "CaciqueGuard (Caddy) isn't set up yet. Run adguard/setup-adguard.sh first."
fi
sleep 5
if docker cp caciquenames:/data/caddy/pki/authorities/local/root.crt "$ACC/cacique-ca.crt" >/dev/null 2>&1; then
    ok "Cacique certificate saved: $ACC/cacique-ca.crt"
    if [ ! -f /usr/local/share/ca-certificates/cacique-ca.crt ] || ! cmp -s "$ACC/cacique-ca.crt" /usr/local/share/ca-certificates/cacique-ca.crt; then
        sudo cp "$ACC/cacique-ca.crt" /usr/local/share/ca-certificates/cacique-ca.crt && sudo update-ca-certificates >/dev/null 2>&1 \
            && ok "This laptop now trusts the Cacique certificate"
    fi
else
    warn "Could not read the Cacique certificate yet (wait a minute and run this again)"
fi

step "6/6  Testing"
if wait_for "http://127.0.0.1:8222/alive" 60; then ok "CaciqueVault answers inside the laptop"; else warn "CaciqueVault not answering yet"; fi
C="$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 --cacert "$ACC/cacique-ca.crt" "https://$IP:8443/alive")"
[ "$C" = "200" ] && ok "Secure door works: https://$IP:8443" || warn "https://$IP:8443 answered $C"

finish
cat <<EOT

 CACIQUEVAULT:  https://$IP:8443    (adults only)

 ONE TIME ON EACH ADULT'S PHONE / COMPUTER - trust the Cacique certificate:
   1. Open  http://$IP/cacique-ca.crt  and download it
   2. iPhone:  Settings -> Profile Downloaded -> Install
               then Settings -> General -> About -> Certificate Trust Settings -> turn ON "Caddy Local Authority"
      Android: Settings -> Security -> Encryption & credentials -> Install a certificate -> CA certificate
      Windows: double-click it -> Install -> Local Machine -> "Trusted Root Certification Authorities"
      Mac:     double-click it -> Keychain "System" -> open it -> Trust -> "Always Trust"

 NEXT: create the accounts (this also invites everyone to CaciqueVault):
   bash ~/elcaciquedeck/accounts/create-accounts.sh

EOT
