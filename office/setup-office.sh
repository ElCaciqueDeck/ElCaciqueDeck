#!/usr/bin/env bash
# ElCaciqueDeck - CaciqueOffice setup (LibreOffice in the browser + private files for every adult)
#   bash ~/elcaciquedeck/office/setup-office.sh
#   CQ_FORCE=1 bash ~/elcaciquedeck/office/setup-office.sh      (install even with less than 12 GB of memory)
# Run again any time (safe): it keeps the files, the database and the settings.
#
#   1. Checks: Docker, Vault drive, CaciqueGuard (Caddy), enough memory
#   2. Settings (.env with home-made passwords, only on this laptop) and folders on the Vault
#   3. Firewall for the secure doors (5445 files, 5446 editor)
#   4. Downloads and starts Nextcloud + Collabora (first start takes a few minutes)
#   5. Configures: https address, editor link, "Enviar a CaciqueDocs" folder, Spanish, no sample files
#   6. Reloads Caddy and tests. Accounts are made next by accounts/create-accounts.sh.
# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
DIR="$REPO/office"
start_report "office-setup"
occ() { docker exec -u www-data caciqueoffice php occ "$@"; }

step "1/6  Checks"
need_docker
need_vault
IP="$(laptop_ip)"
[ -n "$IP" ] && ok "Laptop number: $IP" || fail "Could not find the laptop number (is the network on?)"
[ -d "$REPO/adguard/conf" ] || docker ps -a --format '{{.Names}}' | grep -qx caciquenames \
    || fail "CaciqueGuard (Caddy) isn't set up yet. Run adguard/setup-adguard.sh first."
RAM="$(total_ram_gb)"
if awk "BEGIN{exit !($RAM < 11.5)}" && [ "$CQ_FORCE" != "1" ]; then
    fail "This computer has ${RAM} GB of memory; CaciqueOffice needs about 12 GB. It stays ready in GitHub for a bigger Home Lab (or run with CQ_FORCE=1)."
fi
ok "Memory: ${RAM} GB"
sudo -v || fail "This needs your password."

step "2/6  Settings and folders"
ODIR="$VAULT/office"
mkdir -p "$ODIR/db" "$DATA/office/html" || sudo mkdir -p "$ODIR/db"
sudo mkdir -p "$ODIR/data" && sudo chown 33:33 "$ODIR/data" && sudo chmod 770 "$ODIR/data" \
    || fail "Could not prepare $ODIR/data"
get() { [ -f "$DIR/.env" ] && grep -E "^$1=" "$DIR/.env" | cut -d= -f2-; }
DBPW="$(get OFFICE_DB_PASSWORD)";   [ -n "$DBPW" ] || DBPW="$(random_password)"
ROOTPW="$(get OFFICE_ROOT_PASSWORD)"; [ -n "$ROOTPW" ] || ROOTPW="$(random_password)"
COPW="$(get COLLABORA_PASSWORD)";   [ -n "$COPW" ] || COPW="$(random_password)"
# CaciqueDocs' consume folder: PDFs saved there are archived by Paperless. Without CaciqueDocs, a holding folder.
CONSUME=""
PDIR="$(grep -E '^PAPERLESS_DIR=' "$REPO/paperless/.env" 2>/dev/null | cut -d= -f2-)"
[ -n "$PDIR" ] && [ -d "$PDIR/consume" ] && CONSUME="$PDIR/consume"
[ -n "$CONSUME" ] || { CONSUME="$ODIR/to-docs"; mkdir -p "$CONSUME"; }
sudo chmod 777 "$CONSUME" 2>/dev/null   # Nextcloud (user 33) writes, Paperless (user 1000) reads and removes
cat > "$DIR/.env" <<ENV
# CaciqueOffice settings - written by setup-office.sh, stays on this laptop (never on GitHub)
CACIQUE_IP=$IP
OFFICE_DIR=$ODIR
OFFICE_HTML=$DATA/office/html
OFFICE_TO_DOCS=$CONSUME
OFFICE_DB_PASSWORD=$DBPW
OFFICE_ROOT_PASSWORD=$ROOTPW
COLLABORA_PASSWORD=$COPW
ENV
chmod 600 "$DIR/.env"
ok "Files and database on the Vault drive: $ODIR"
ok "\"Enviar a CaciqueDocs\" folder -> $CONSUME"
grep -q '^CACIQUE_IP=' "$REPO/adguard/.env" 2>/dev/null || printf 'CACIQUE_IP=%s\n' "$IP" > "$REPO/adguard/.env"

step "3/6  Firewall"
open_port 5445 "CaciqueOffice"
open_port 5446 "CaciqueOffice editor"

step "4/6  Downloading and starting (first time: 2-3 GB, then a few minutes to set itself up)"
cd "$DIR" || fail "Can't open $DIR"
docker compose pull || fail "Download failed. Check the internet and run this again."
docker compose up -d || fail "Could not start CaciqueOffice."
i=0
until curl -s --max-time 5 http://127.0.0.1:8085/status.php | grep -q '"installed":true'; do
    i=$((i+10)); [ "$i" -gt 900 ] && fail "Nextcloud did not finish setting itself up (see: docker logs caciqueoffice)"
    sleep 10
done
ok "Nextcloud is installed"

step "5/6  Configuring"
occ config:system:set trusted_domains 0 --value="$IP" >/dev/null
occ config:system:set trusted_domains 1 --value="$IP:5445" >/dev/null
occ config:system:set trusted_domains 2 --value="localhost" >/dev/null
occ config:system:set overwriteprotocol --value=https >/dev/null
occ config:system:set overwritehost --value="$IP:5445" >/dev/null
occ config:system:set overwrite.cli.url --value="https://$IP:5445" >/dev/null
occ config:system:set trusted_proxies 0 --value="172.16.0.0/12" >/dev/null
occ config:system:set default_language --value=es >/dev/null
occ config:system:set default_phone_region --value=PR >/dev/null
occ config:system:set skeletondirectory --value="" >/dev/null          # no sample files in new accounts
occ config:system:set maintenance_window_start --type=integer --value=6 >/dev/null
ok "Secure address: https://$IP:5445"
# the same simple password rules as the other Cacique apps (and no internet check of passwords)
occ config:app:set password_policy minLength --value=8 >/dev/null 2>&1
occ config:app:set password_policy enforceHaveIBeenPwned --value=0 >/dev/null 2>&1
occ config:app:set password_policy enforceNonCommonPassword --value=0 >/dev/null 2>&1
# the LibreOffice editor
occ app:install richdocuments >/dev/null 2>&1 || occ app:enable richdocuments >/dev/null 2>&1
occ config:app:set richdocuments wopi_url --value="https://$IP:5446" >/dev/null
occ config:app:set richdocuments public_wopi_url --value="https://$IP:5446" >/dev/null
occ config:app:set richdocuments disable_certificate_verification --value=yes >/dev/null
occ richdocuments:activate-config >/dev/null 2>&1
occ app:list 2>/dev/null | grep -q "richdocuments" && ok "LibreOffice editor connected" || warn "LibreOffice editor app not installed (needs internet; run this again)"
# the bridge to CaciqueDocs
occ app:enable files_external >/dev/null 2>&1
if ! occ files_external:list 2>/dev/null | grep -q "Enviar a CaciqueDocs"; then
    occ files_external:create "/Enviar a CaciqueDocs" local null::null -c datadir=/mnt/caciquedocs >/dev/null \
        && ok "Folder \"Enviar a CaciqueDocs\" added for everyone" || warn "Could not add the CaciqueDocs folder"
else
    ok "Folder \"Enviar a CaciqueDocs\" already there"
fi

step "6/6  Secure doors and test"
(cd "$REPO/adguard" && docker compose up -d --force-recreate caddy >"$REPORT_DIR/run-caddy-office.log" 2>&1) \
    && ok "Caddy reloaded (5445 and 5446)" || fail "Caddy reload failed - see $REPORT_DIR/run-caddy-office.log"
sleep 5
C="$(curl -sk -o /dev/null -w '%{http_code}' --max-time 10 "https://$IP:5445/status.php")"
[ "$C" = "200" ] && ok "Files door works: https://$IP:5445" || warn "https://$IP:5445 answered $C"
C="$(curl -sk -o /dev/null -w '%{http_code}' --max-time 10 "https://$IP:5446/hosting/discovery")"
[ "$C" = "200" ] && ok "Editor door works: https://$IP:5446" || warn "https://$IP:5446 answered $C (the editor can take a minute)"
echo
echo "  Open: https://$IP:5445   - accounts (ElCaciqueAdmin + adults) are made by: bash ~/elcaciquedeck/accounts/create-accounts.sh"
finish
